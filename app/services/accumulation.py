"""Cumulative observation counts by year and phylum from FinBIF warehouse aggregate."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from urllib.parse import urlencode

from app.services.finbif_client import FinbifApiError, get_json
from app.services.observers_taxa import get_taxon_scientific_name, normalize_taxon_id_for_api

_API_BASE = "https://api.laji.fi/warehouse/query/unit/aggregate"

_TOP_N_PHYLA = 10
_PAGE_SIZE = 1000


def _base_query_items() -> list[tuple[str, str | list[str]]]:
    return [
        (
            "aggregateBy",
            [
                "gathering.conversions.year",
                "unit.linkings.taxon.phylumId",
            ],
        ),
        ("orderBy", "gathering.conversions.year ASC"),
        ("onlyCount", "true"),
        ("taxonCounts", "false"),
        ("gatheringCounts", "false"),
        ("pairCounts", "false"),
        ("atlasCounts", "false"),
        ("excludeNulls", "true"),
        ("pessimisticDateRangeHandling", "false"),
        ("cache", "true"),
        ("useIdentificationAnnotations", "true"),
        ("includeSubTaxa", "true"),
        ("includeNonValidTaxa", "true"),
        ("individualCountMin", "1"),
        ("includeNullLoadDates", "false"),
        ("qualityIssues", "NO_ISSUES"),
        ("countryId", "ML.206"),
        ("wild", "WILD,WILD_UNKNOWN"),
        ("recordQuality", "COMMUNITY_VERIFIED,NEUTRAL,EXPERT_VERIFIED"),
        ("higherTaxon", "false"),
    ]


def _fetch_year_phylum(*, page: int) -> dict:
    items = list(_base_query_items())
    items.append(("pageSize", str(_PAGE_SIZE)))
    items.append(("page", str(page)))
    url = f"{_API_BASE}?{urlencode(items, doseq=True)}"
    return get_json(url)


def _parse_phylum_id(raw: object) -> str | None:
    """Warehouse aggregate may return phylum id as string, full URI, or nested object."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        for key in ("id", "qname", "value"):
            v = raw.get(key)
            if isinstance(v, str) and v.strip():
                return _parse_phylum_id(v)
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    s = raw.strip()
    if not s:
        return None
    nid = normalize_taxon_id_for_api(s)
    return nid if nid else None


def get_cumulative_series_by_phylum() -> dict[str, object]:
    """Cumulative unit counts per calendar year for the top phyla (by total units in query).

    Returns ``years`` (shared x-axis), ``series`` (each: ``phylum_id``, ``scientific_name``, ``cumulative``),
    and optional ``error``.
    """
    max_year = datetime.now().year + 1
    rows: list[tuple[int, str, int]] = []
    page = 1

    try:
        while page <= 200:
            data = _fetch_year_phylum(page=page)
            results = data.get("results", [])
            if not isinstance(results, list):
                break
            for item in results:
                if not isinstance(item, dict):
                    continue
                agg = item.get("aggregateBy")
                if not isinstance(agg, dict):
                    continue
                raw_y = agg.get("gathering.conversions.year")
                if raw_y is None:
                    continue
                try:
                    y = int(raw_y)
                except (TypeError, ValueError):
                    continue
                if y < 1600 or y > max_year:
                    continue
                pid = _parse_phylum_id(agg.get("unit.linkings.taxon.phylumId"))
                if not pid:
                    continue
                c = item.get("count", 0)
                if isinstance(c, bool):
                    continue
                if isinstance(c, (int, float)):
                    cnt = int(c)
                else:
                    try:
                        cnt = int(str(c))
                    except ValueError:
                        cnt = 0
                rows.append((y, pid, cnt))
            if len(results) < _PAGE_SIZE:
                break
            page += 1
    except FinbifApiError as e:
        return {"years": [], "series": [], "error": str(e)}

    totals: defaultdict[str, int] = defaultdict(int)
    by_phylum_year: defaultdict[str, defaultdict[int, int]] = defaultdict(lambda: defaultdict(int))
    year_set: set[int] = set()

    for y, pid, cnt in rows:
        year_set.add(y)
        totals[pid] += cnt
        by_phylum_year[pid][y] += cnt

    if not year_set:
        return {"years": [], "series": [], "error": None}

    ranked = sorted(totals.keys(), key=lambda p: totals[p], reverse=True)
    top_ids = ranked[:_TOP_N_PHYLA]
    years_sorted = sorted(year_set)

    series_out: list[dict[str, object]] = []
    for pid in top_ids:
        scientific_name = get_taxon_scientific_name(pid) or pid
        ymap = by_phylum_year[pid]
        cumulative: list[int] = []
        run = 0
        for y in years_sorted:
            run += int(ymap.get(y, 0))
            cumulative.append(run)
        series_out.append(
            {
                "phylum_id": pid,
                "scientific_name": scientific_name,
                "cumulative": cumulative,
            }
        )

    return {
        "years": years_sorted,
        "series": series_out,
        "error": None,
    }
