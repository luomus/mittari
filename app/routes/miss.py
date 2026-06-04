from flask import Blueprint, render_template, request

from app.extensions import cache
from app.services import miss as miss_service
from app.services import observers_taxa
from app.services.taxon_id import normalize_taxon_id

bp = Blueprint("miss", __name__, url_prefix="/miss")

CACHE_20_HOURS = 20 * 3600

_DEFAULT_LAT = 60.6267
_DEFAULT_LON = 25.2862
_DEFAULT_TAXON = "MX.1"
_DEFAULT_SINCE_YEAR = 2001
_DEFAULT_NEAR = 25
_DEFAULT_FAR = 100

_INNER_KM_MIN = 0
_INNER_KM_MAX = 50
_OUTER_KM_MIN = 0
_OUTER_KM_MAX = 100
_NONINT_DEFAULT_NEAR = 10
_NONINT_DEFAULT_FAR = 30


def _normalize_near_far_km(raw_near: str, raw_far: str) -> tuple[int, int]:
    """Integers in range; non-integer strings → 10 km / 30 km."""

    def strict_uint(s: str) -> int | None:
        t = s.strip()
        if not t or not t.isdigit():
            return None
        return int(t)

    n = strict_uint(raw_near)
    if n is None:
        near_km = _NONINT_DEFAULT_NEAR
    else:
        near_km = max(_INNER_KM_MIN, min(_INNER_KM_MAX, n))

    f = strict_uint(raw_far)
    if f is None:
        far_km = _NONINT_DEFAULT_FAR
    else:
        far_km = max(_OUTER_KM_MIN, min(_OUTER_KM_MAX, f))

    return near_km, far_km


def _parse_miss_args() -> tuple[dict[str, object] | None, str | None]:
    """Return (params dict, error Finnish) — error means skip FinBIF."""
    raw_lat = request.args.get("lat", type=str, default=str(_DEFAULT_LAT))
    raw_lon = request.args.get("lon", type=str, default=str(_DEFAULT_LON))
    raw_taxon = request.args.get("taxon_id", type=str, default=_DEFAULT_TAXON)
    raw_since = request.args.get("since_year", type=str, default=str(_DEFAULT_SINCE_YEAR))
    raw_near = request.args.get("near", type=str, default=str(_DEFAULT_NEAR))
    raw_far = request.args.get("far", type=str, default=str(_DEFAULT_FAR))

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
    except ValueError:
        return None, "Leveys- tai pituusaste ei ole kelvollinen luku."

    if lat < 0 or lon < 0:
        return None, "Leveys- ja pituusasteen oletetaan olevan positiivisia (Suomi)."

    lat_r = round(lat, 2)
    lon_r = round(lon, 2)

    try:
        since_year = int(raw_since)
    except ValueError:
        return None, "since_year ei ole kelvollinen kokonaisluku."

    near_km, far_km = _normalize_near_far_km(raw_near, raw_far)

    tid = normalize_taxon_id(raw_taxon or "")
    if tid is None:
        return None, "Taksonin tunniste ei kelpaa."

    return (
        {
            "lat": lat_r,
            "lon": lon_r,
            "taxon_id": tid,
            "since_year": since_year,
            "near_km": near_km,
            "far_km": far_km,
        },
        None,
    )


@bp.route("/")
@cache.cached(timeout=CACHE_20_HOURS, query_string=True)
def miss_page():
    parsed, parse_err = _parse_miss_args()
    if parse_err or parsed is None:
        raw_taxon = (request.args.get("taxon_id") or _DEFAULT_TAXON).strip()
        return render_template(
            "miss.html",
            lat=request.args.get("lat") or str(_DEFAULT_LAT),
            lon=request.args.get("lon") or str(_DEFAULT_LON),
            taxon_id=raw_taxon or _DEFAULT_TAXON,
            taxon_label=observers_taxa.get_taxon_display_label(raw_taxon)
            if raw_taxon
            else None,
            since_year=request.args.get("since_year") or str(_DEFAULT_SINCE_YEAR),
            near_km=request.args.get("near") or str(_DEFAULT_NEAR),
            far_km=request.args.get("far") or str(_DEFAULT_FAR),
            rows=[],
            error=parse_err or "Virhe.",
            laji_obs_coordinates=None,
        )

    result = miss_service.missing_species_between_rings(
        lat=float(parsed["lat"]),
        lon=float(parsed["lon"]),
        taxon_id=str(parsed["taxon_id"]),
        since_year=int(parsed["since_year"]),
        near_km=int(parsed["near_km"]),
        far_km=int(parsed["far_km"]),
    )
    taxon_label = observers_taxa.get_taxon_display_label(str(parsed["taxon_id"]))
    laji_obs_coordinates = miss_service.laji_observation_list_outer_box_coordinates(
        float(parsed["lat"]),
        float(parsed["lon"]),
        int(parsed["far_km"]),
    )

    return render_template(
        "miss.html",
        lat=parsed["lat"],
        lon=parsed["lon"],
        taxon_id=parsed["taxon_id"],
        taxon_label=taxon_label,
        since_year=parsed["since_year"],
        near_km=parsed["near_km"],
        far_km=parsed["far_km"],
        rows=result["rows"],
        error=result.get("error"),
        laji_obs_coordinates=laji_obs_coordinates,
    )
