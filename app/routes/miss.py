from flask import Blueprint, render_template, request

from app.extensions import cache
from app.services import miss as miss_service
from app.services import observers_taxa

bp = Blueprint("miss", __name__, url_prefix="/miss")

CACHE_20_HOURS = 20 * 3600

_DEFAULT_LAT = 60.6267
_DEFAULT_LON = 25.2862
_DEFAULT_TAXON = "MX.1"
_DEFAULT_SINCE_YEAR = 2001
_DEFAULT_NEAR = 25
_DEFAULT_FAR = 100


def _parse_miss_args() -> tuple[dict[str, object] | None, str | None]:
    """Return (params dict, error Finnish) — error means skip FinBIF."""
    raw_lat = request.args.get("lat", type=str, default=str(_DEFAULT_LAT))
    raw_lon = request.args.get("lon", type=str, default=str(_DEFAULT_LON))
    raw_taxon = request.args.get("taxon", type=str, default=_DEFAULT_TAXON)
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

    lat_r = round(lat, 4)
    lon_r = round(lon, 4)

    try:
        since_year = int(raw_since)
    except ValueError:
        return None, "since_year ei ole kelvollinen kokonaisluku."

    try:
        near_km = int(raw_near)
        far_km = int(raw_far)
    except ValueError:
        return None, "near tai far ei ole kelvollinen kokonaisluku."

    taxon_id = (raw_taxon or "").strip()
    if not taxon_id:
        return None, "Taksoni puuttuu."

    return (
        {
            "lat": lat_r,
            "lon": lon_r,
            "taxon_id": taxon_id,
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
        raw_taxon = (request.args.get("taxon") or _DEFAULT_TAXON).strip()
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
    )
