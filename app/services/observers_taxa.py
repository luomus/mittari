"""Business logic: observer species counts under a taxon, from FinBIF warehouse aggregate.

Taxon identifiers (e.g. ``MX.71950``) for ``taxonId`` / URL paths should be taken from
FinBIF ``GET /autocomplete/taxa`` result objects' ``id`` field — not ``value`` or display
strings alone.
"""


from __future__ import annotations

import os
from urllib.parse import quote, urlencode

from app.services.finbif_client import FinbifApiError, get_json

_API_BASE = "https://api.laji.fi/warehouse/query/unit/aggregate"
_TAXA_BASE = "https://api.laji.fi/taxa"

DEFAULT_TAXON_ID = "MX.37600"


def _hidden_name_fold_set() -> set[str]:
    """Names from ``HIDDEN_NAMES`` (``;``-separated) for case-insensitive exact match."""
    raw = (os.environ.get("HIDDEN_NAMES") or "").strip()
    if not raw:
        return set()
    return {p.strip().casefold() for p in raw.split(";") if p.strip()}


def _taxon_id_param(taxon_id: str) -> str:
    """FinBIF accepts short qnames (e.g. MX.37600) or full taxon URIs."""
    tid = taxon_id.strip()
    if tid.startswith("http://") or tid.startswith("https://"):
        return tid
    return tid

def get_taxon_display_label(taxon_id: str) -> str | None:
    """Resolve taxon id to ``scientific name (Finnish vernacular)`` via ``GET /taxa/{id}``.

    Returns ``None`` if the request fails or names are missing.
    ``Accept-Language: fi`` is set on the HTTP client so ``vernacularName`` is Finnish when available.
    """
    tid = taxon_id.strip()
    if not tid:
        return None
    params = {
        "checklistVersion": "current",
        "includeMedia": "false",
        "includeDescriptions": "false",
        "includeRedListEvaluations": "false",
    }
    path = quote(tid, safe="")
    url = f"{_TAXA_BASE}/{path}?{urlencode(params)}"
    try:
        data = get_json(url)
    except FinbifApiError:
        return None

    raw_sci = data.get("scientificName")
    if isinstance(raw_sci, str):
        sci = raw_sci.strip()
    elif raw_sci is not None:
        sci = str(raw_sci).strip()
    else:
        sci = ""

    vern_raw = data.get("vernacularName")
    if isinstance(vern_raw, str):
        vern = vern_raw.strip()
    elif isinstance(vern_raw, dict):
        v = vern_raw.get("fi") or vern_raw.get("FI")
        vern = str(v).strip() if v is not None else ""
    elif vern_raw is not None:
        vern = str(vern_raw).strip()
    else:
        vern = ""

    if sci and vern:
        return f"{sci} ({vern})"
    if sci:
        return sci
    return None



def _fetch_aggregate(*, taxon_id: str, year: int | None) -> dict:
    params = {
        "aggregateBy": "gathering.team.memberName",
        "orderBy": "speciesCount DESC",
        "onlyCount": "true",
        "taxonCounts": "true",
        "gatheringCounts": "false",
        "pairCounts": "false",
        "atlasCounts": "false",
        "excludeNulls": "true",
        "pessimisticDateRangeHandling": "false",
        "pageSize": "100",
        "page": "1",
        "cache": "true",
        "useIdentificationAnnotations": "true",
        "includeSubTaxa": "true",
        "includeNonValidTaxa": "true",
        "individualCountMin": "1",
        "includeNullLoadDates": "false",
        "qualityIssues": "NO_ISSUES",
        "countryId": "ML.206",
        "wild": "WILD,WILD_UNKNOWN",
        "recordQuality": "COMMUNITY_VERIFIED,NEUTRAL,EXPERT_VERIFIED",
        "higherTaxon": "false",
        "taxonId": _taxon_id_param(taxon_id),
    }
    if year is not None:
        params["time"] = str(year)
    url = f"{_API_BASE}?{urlencode(params)}"
    return get_json(url)


def get_observer_taxa_stats(taxon_id: str, year: int | None) -> dict[str, object]:
    """Return ranked observers for the given taxon, optionally for one calendar year.

    If ``year`` is ``None``, the FinBIF query omits ``time`` (all years).

    Returns a dict with ``rows`` (list of ``name`` / ``species_count``),
    optional ``total`` from the API, and optional ``error`` (Finnish message).
    """
    if year is not None and year < 1500:
        return {
            "rows": [],
            "total": 0,
            "error": "Vuosiluku ei kelpaa.",
        }

    try:
        data = _fetch_aggregate(taxon_id=taxon_id, year=year)
    except FinbifApiError as e:
        return {"rows": [], "total": None, "error": str(e)}

    total = data.get("total", 0)
    results = list(data.get("results", []))

    taxon_counts = [
        r["taxonCount"]
        for r in results
        if isinstance(r.get("taxonCount"), (int, float))
    ]

    # Since the API sorts results based on taxon count, not species count, we need to filter out the results with less than the minimum taxon count. Otherwise someone with less species might be included even when someone with more species but with less taxa are not on the first page of API results.
    if taxon_counts:
        min_taxon = min(taxon_counts)
        filtered = [r for r in results if r.get("speciesCount", 0) >= min_taxon]
    else:
        filtered = results

    rows: list[dict[str, object]] = []
    for item in filtered:
        name = item.get("aggregateBy", {}).get("gathering.team.memberName", "")
        species = item.get("speciesCount", 0)
        if isinstance(species, (int, float)):
            scount = int(species)
        else:
            try:
                scount = int(str(species))
            except ValueError:
                scount = 0
        rows.append({"name": str(name), "species_count": scount})

    hidden = _hidden_name_fold_set()
    if hidden:
        out: list[dict[str, object]] = []
        for row in rows:
            nm = row["name"]
            if isinstance(nm, str) and nm.strip().casefold() in hidden:
                out.append({"name": "piilotettu", "species_count": row["species_count"]})
            else:
                out.append(dict(row))
        rows = out

    return {
        "rows": rows,
        "error": None,
    }


