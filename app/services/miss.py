"""Species present in an outer radius but not in an inner radius (FinBIF warehouse aggregate)."""

from __future__ import annotations

import datetime
import math
from urllib.parse import urlencode

from app.services.finbif_client import FinbifApiError, get_json

_API_BASE = "https://api.laji.fi/warehouse/query/unit/aggregate"


def _taxon_id_param(taxon_id: str) -> str:
    tid = taxon_id.strip()
    if tid.startswith("http://") or tid.startswith("https://"):
        return tid
    return tid


def bounding_box(lat: float, lon: float, box_size_km: float) -> tuple[float, float, float, float]:
    r_earth = 6371.0
    lat_rad = math.radians(lat)
    angular_distance = box_size_km / r_earth
    lat_min = lat - math.degrees(angular_distance)
    lat_max = lat + math.degrees(angular_distance)
    delta_lon = math.degrees(angular_distance / math.cos(lat_rad))
    lon_min = lon - delta_lon
    lon_max = lon + delta_lon
    return (
        round(lat_min, 4),
        round(lat_max, 4),
        round(lon_min, 4),
        round(lon_max, 4),
    )


def _coordinates_param(lat: float, lon: float, radius_km: float) -> str:
    lat_min, lat_max, lon_min, lon_max = bounding_box(lat, lon, radius_km)
    return f"{lat_min}:{lat_max}:{lon_min}:{lon_max}:WGS84:1"


def _fetch_species_counts(
    *,
    taxon_id: str,
    lat: float,
    lon: float,
    radius_km: float,
    since_year: int,
    current_year: int,
) -> dict[str, dict[str, object]]:
    params = {
        "aggregateBy": ",".join(
            [
                "unit.linkings.taxon.id",
                "unit.linkings.taxon.nameFinnish",
                "unit.linkings.taxon.scientificName",
            ]
        ),
        "onlyCount": "true",
        "taxonCounts": "false",
        "gatheringCounts": "false",
        "pairCounts": "false",
        "atlasCounts": "false",
        "excludeNulls": "true",
        "pessimisticDateRangeHandling": "false",
        "pageSize": "1000",
        "page": "1",
        "cache": "true",
        "taxonId": _taxon_id_param(taxon_id),
        "useIdentificationAnnotations": "true",
        "includeSubTaxa": "true",
        "includeNonValidTaxa": "true",
        "taxonRankId": "MX.species",
        "countryId": "ML.206",
        "time": f"{since_year}/{current_year}",
        "individualCountMin": "1",
        "coordinates": _coordinates_param(lat, lon, radius_km),
        "qualityIssues": "NO_ISSUES",
    }
    url = f"{_API_BASE}?{urlencode(params)}"
    data = get_json(url)
    results = data.get("results", [])
    if not isinstance(results, list):
        return {}

    out: dict[str, dict[str, object]] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        agg = row.get("aggregateBy")
        if not isinstance(agg, dict):
            continue
        tid = agg.get("unit.linkings.taxon.id")
        if tid is None:
            continue
        tid_s = str(tid)
        count_raw = row.get("count", 0)
        if isinstance(count_raw, (int, float)):
            count = int(count_raw)
        else:
            try:
                count = int(str(count_raw))
            except ValueError:
                count = 0
        fi = agg.get("unit.linkings.taxon.nameFinnish")
        sci = agg.get("unit.linkings.taxon.scientificName")
        out[tid_s] = {
            "count": count,
            "fi": str(fi) if fi is not None else "",
            "sci": str(sci) if sci is not None else "",
        }
    return out


def missing_species_between_rings(
    *,
    lat: float,
    lon: float,
    taxon_id: str,
    since_year: int,
    near_km: int,
    far_km: int,
) -> dict[str, object]:
    """Return ``rows`` (outer-only species), ``error`` (Finnish message if any)."""
    current_year = datetime.datetime.now().year
    if since_year < 1900 or since_year > current_year:
        return {
            "rows": [],
            "error": "Vuosiluku tulee olla välillä 1900 ja kuluva vuosi.",
        }
    if near_km < 1 or far_km < 1:
        return {
            "rows": [],
            "error": "Säteen täytyy olla vähintään 1 km.",
        }
    if far_km <= near_km:
        return {
            "rows": [],
            "error": "Ulomman säteen täytyy olla suurempi kuin sisemmän.",
        }

    try:
        inner = _fetch_species_counts(
            taxon_id=taxon_id,
            lat=lat,
            lon=lon,
            radius_km=float(near_km),
            since_year=since_year,
            current_year=current_year,
        )
        outer = _fetch_species_counts(
            taxon_id=taxon_id,
            lat=lat,
            lon=lon,
            radius_km=float(far_km),
            since_year=since_year,
            current_year=current_year,
        )
    except FinbifApiError as e:
        return {"rows": [], "error": str(e)}

    rows: list[dict[str, object]] = []
    for tid, info in outer.items():
        if tid in inner:
            continue
        rows.append(
            {
                "taxon_id": tid,
                "fi": info.get("fi", ""),
                "sci": info.get("sci", ""),
                "count": info.get("count", 0),
            }
        )

    rows.sort(key=lambda r: int(r.get("count", 0)), reverse=True)

    return {"rows": rows, "error": None}
