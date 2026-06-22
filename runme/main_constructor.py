"""
This script creates a src database and fills with raw data from referenced files.
Do not use DatabaseConstructor class unless you want to create a new database.
"""

import sys
import os

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import csv
import struct
csv.field_size_limit(100 * 1024 * 1024)  # 100 MB – EWKB hex geometries can be large
from src.config_loader import LOG_LEVEL, CSV_FILE_LIST, get_country_code
from raw_data.municipal_register.join_regiostar_gemeindeverz import create_municipal_register
from src.database.database_constructor import DatabaseConstructor
from src import utils


logger = utils.create_logger(name="main_constructor", log_file="log.txt", log_level=LOG_LEVEL)


def _count_unique_plz_in_csv(csv_path: str) -> int:
    """Return number of unique non-empty `plz` values in a postcode CSV."""
    unique_plz: set[str] = set()
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "plz" not in reader.fieldnames:
            return 0
        for row in reader:
            value = (row.get("plz") or "").strip()
            if value:
                unique_plz.add(value)
    return len(unique_plz)


def _postcode_csv_state_code_stats(csv_path: str) -> tuple[bool, int]:
    """Return whether a postcode CSV has a state_code column and how many rows populate it."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "state_code" not in reader.fieldnames:
            return False, 0
        populated = 0
        for row in reader:
            if (row.get("state_code") or "").strip():
                populated += 1
    return True, populated


def _detect_wkb_geom_type(ewkb_hex: str) -> str | None:
    """Best-effort geometry type detection from WKB/EWKB hex."""
    if not ewkb_hex:
        return None

    raw_hex = str(ewkb_hex).strip()
    if raw_hex.startswith("\\x"):
        raw_hex = raw_hex[2:]

    try:
        raw = bytes.fromhex(raw_hex)
    except ValueError:
        return None

    if len(raw) < 5:
        return None

    byte_order = raw[0]
    if byte_order == 0:
        geom_type = struct.unpack(">I", raw[1:5])[0]
    elif byte_order == 1:
        geom_type = struct.unpack("<I", raw[1:5])[0]
    else:
        return None

    base_type = geom_type & 0xFF
    return {
        1: "Point",
        3: "Polygon",
        6: "MultiPolygon",
    }.get(base_type, f"GeometryType({base_type})")


def _sample_geom_type_in_csv(csv_path: str) -> str | None:
    """Read the first non-empty geometry from a postcode CSV and detect its type."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "geom" not in reader.fieldnames:
            return None
        for row in reader:
            geom_hex = (row.get("geom") or "").strip()
            if geom_hex:
                return _detect_wkb_geom_type(geom_hex)
    return None


def _select_postcode_csv(country: str) -> str | None:
    """Choose the best postcode CSV, preferring polygonal geometry over points."""
    candidates = [
        os.path.join("raw_data", country, f"postcode_{country}.csv"),
        os.path.join("raw_data", country, "postcode.csv"),
        os.path.join("raw_data", "postcode.csv"),
    ]

    existing: list[tuple[str, str | None]] = []
    for csv_path in candidates:
        if os.path.exists(csv_path):
            existing.append((csv_path, _sample_geom_type_in_csv(csv_path)))

    if not existing:
        return None

    for csv_path, geom_type in existing:
        if geom_type in {"Polygon", "MultiPolygon"}:
            if geom_type == "Polygon":
                logger.warning(
                    "Selected postcode CSV %s with %s geometry; postcode schema expects MultiPolygon, so preparation should promote polygons to multipolygons.",
                    csv_path,
                    geom_type,
                )
            return csv_path

    known_types = [geom_type for _, geom_type in existing if geom_type]
    if known_types:
        logger.error(
            "All available postcode CSV files for %s have non-polygon geometry types: %s",
            country,
            ", ".join(f"{path}={geom_type}" for path, geom_type in existing),
        )
        return None

    fallback_path, fallback_geom_type = existing[0]
    logger.warning(
        "No polygonal postcode CSV found for %s. Falling back to %s (sample geometry type: %s).",
        country,
        fallback_path,
        fallback_geom_type or "unknown",
    )
    return fallback_path


def _load_regions_config() -> dict:
    """Load datapipeline regions configuration if present."""
    import yaml
    from pathlib import Path

    config_path = Path(PROJECT_ROOT) / "datapipeline" / "config" / "regions.yaml"
    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def _refresh_country_postcodes(
    sgc: DatabaseConstructor,
    country: str,
    state: str | None,
    regions: dict,
) -> str:
    """Refresh country postcode data when the current DB coverage is incomplete."""
    logger.info(f"### POPULATE DB WITH POSTCODE DATA ({country}) ###")
    country_code = get_country_code(country)

    logger.info(f"### PREPARE STATE REGISTRY ({country}/{state}) ###")
    state_pre_sync_stats = sgc.dbc.ensure_state_relationships(country=country, state=state, state_name=state)
    logger.info(f"State registry pre-sync: {state_pre_sync_stats}")

    postcode_state_code_count = 0
    with sgc.dbc.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM postcode WHERE country_code = %s", (country_code,))
        postcode_count = cur.fetchone()[0]
        if bool(regions.get(country, {}).get("states")):
            cur.execute(
                """
                SELECT COUNT(*)
                FROM postcode
                WHERE country_code = %s
                  AND COALESCE(BTRIM(state_code), '') <> ''
                """,
                (country_code,),
            )
            postcode_state_code_count = cur.fetchone()[0]

    postcode_csv = _select_postcode_csv(country)
    if not postcode_csv:
        logger.warning(f"No postcode file found for {country}. Run: make prepare-country COUNTRY={country}")

    if postcode_csv and os.path.exists(postcode_csv):
        expected_count = _count_unique_plz_in_csv(postcode_csv)
        should_refresh = postcode_count == 0
        reason = "no existing rows"
        country_has_states = bool(regions.get(country, {}).get("states"))
        csv_has_state_code, csv_state_code_count = _postcode_csv_state_code_stats(postcode_csv)
        csv_has_populated_state_codes = csv_state_code_count > 0

        if country_has_states and not csv_has_populated_state_codes:
            detail = (
                "missing state_code column"
                if not csv_has_state_code
                else "state_code column has no populated values"
            )
            if postcode_count == 0:
                logger.error(
                    "Refusing postcode import for %s from %s: %s. "
                    "State-scoped countries require prepared postcode data. "
                    "Run: make prepare-country COUNTRY=%s",
                    country_code,
                    postcode_csv,
                    detail,
                    country,
                )
                sys.exit(1)

            logger.warning(
                "Skipping postcode refresh for %s from %s: %s. "
                "Refreshing from an unscoped CSV would clear other states. "
                "Run: make prepare-country COUNTRY=%s",
                country_code,
                postcode_csv,
                detail,
                country,
            )
            should_refresh = False

        if postcode_count > 0 and expected_count > 0 and postcode_count != expected_count:
            should_refresh = True
            reason = f"count mismatch (db={postcode_count}, csv_unique_plz={expected_count})"

        if (
            country_has_states
            and csv_has_populated_state_codes
            and postcode_count > 0
            and postcode_state_code_count != csv_state_code_count
        ):
            should_refresh = True
            reason = (
                "state_code coverage mismatch "
                f"(db_state_coded={postcode_state_code_count}, csv_state_coded={csv_state_code_count})"
            )

        if country_has_states and not csv_has_populated_state_codes:
            should_refresh = False

        if should_refresh:
            logger.info(
                "Refreshing postcode data for %s from %s (%s)",
                country_code,
                postcode_csv,
                reason,
            )
            csv_file_list = [{"path": postcode_csv, "table_name": "postcode"}]
            sgc.csv_to_db(csv_file_list, country_code=country_code, skip_delete=False)
        else:
            logger.info(
                "Postcode data already exists for %s (%s rows, csv_unique_plz=%s) - skipping import",
                country_code,
                postcode_count,
                expected_count,
            )
    else:
        logger.warning(f"Postcode file not found. Run: make prepare-country COUNTRY={country}")

    logger.info(f"### SYNC STATE REGISTRY ({country}/{state}) ###")
    state_sync_stats = sgc.dbc.ensure_state_relationships(country=country, state=state, state_name=state)
    logger.info(f"State registry sync: {state_sync_stats}")
    return country_code


def main_legacy():
    """Original database construction using legacy file paths."""
    ### Create constructor class
    sgc = DatabaseConstructor()

    ### Create database with predefined table structure
    logger.info("### CREATE ALL TABLES ###")
    sgc.create_table(table_name="all")

    ### Add defined csv raw data from CSV_FILE_LIST to the database
    logger.info("### POPULATE DB WITH CSV RAW DATA ###")
    sgc.csv_to_db(CSV_FILE_LIST)

    ### Add transformer data from geojson to the database
    logger.info("### QUERY TRANSFORMERS AND INSERT THEM INTO DB (~50 min if processing new trafo data) ###")
    sgc.transformers_to_db()

    ### Create table with data from osm
    logger.info("### POPULATE public_2po_4pgr TABLE (~30 min) ###")
    sgc.create_public_2po_table()

    ### Transform these data into our ways table
    logger.info("### PROCESS WAYS AND INSERTING THEM INTO ways TABLE ###")
    sgc.ways_to_db()

    ### Add additional required sql functions to the database
    logger.info("### DUMP NECESSARY FUNCTIONS INTO DB ###")
    sgc.dump_functions()

    ### Create table with entries of all German municipalities and cities
    logger.info("### FILL municipal_register TABLE ###")
    create_municipal_register()

    logger.info("### DONE ###")


def main_datapipeline(country: str = "germany", state: str = None):
    """
    Database construction using datapipeline output.

    Args:
        country: Country name (e.g., 'germany', 'netherlands')
        state: State name (e.g., 'hamburg', 'noord_holland')
    """
    regions = _load_regions_config()
    if regions:
        if country not in regions:
            logger.error(f"Invalid country '{country}'. Available countries: {', '.join(regions.keys())}")
            sys.exit(1)
        if state and state not in regions[country].get("states", {}):
            valid_states = list(regions[country].get("states", {}).keys())
            logger.error(f"Invalid state '{state}' for country '{country}'. Available states: {', '.join(valid_states)}")
            sys.exit(1)

    ### Create constructor class
    sgc = DatabaseConstructor()

    ### Create database with predefined table structure
    logger.info("### CREATE ALL TABLES ###")
    sgc.create_table(table_name="all")

    country_code = _refresh_country_postcodes(sgc, country=country, state=state, regions=regions)

    ### Add building data from datapipeline
    logger.info(f"### LOAD BUILDINGS FROM DATAPIPELINE ({country}/{state}) ###")
    sgc.buildings_from_datapipeline(country=country, state=state)

    ### Add transformer data from datapipeline
    logger.info(f"### LOAD TRANSFORMERS FROM DATAPIPELINE ({country}/{state}) ###")
    sgc.transformers_from_datapipeline(country=country, state=state)

    ### Load ways from datapipeline
    logger.info(f"### LOAD WAYS FROM DATAPIPELINE ({country}/{state}) ###")
    sgc.ways_from_datapipeline(country=country, state=state)

    ### Assign state_code to postcodes based on building locations
    logger.info(f"### ASSIGN STATE_CODE TO POSTCODES ({country}/{state}) ###")
    sgc.assign_state_code_to_postcodes(country=country, state=state)

    ### Re-sync relations after postcode updates
    logger.info(f"### FINALIZE STATE RELATIONS ({country}/{state}) ###")
    state_finalize_stats = sgc.dbc.ensure_state_relationships(country=country, state=state, state_name=state)
    logger.info(f"State relation finalize: {state_finalize_stats}")

    ### Ensure version exists
    sgc.dbc.insert_version_if_not_exists()
    
    ### (connecting transformers via road network) instead of importing from OSM

    ### Add additional required sql functions to the database
    logger.info("### DUMP NECESSARY FUNCTIONS INTO DB ###")
    sgc.dump_functions()

    ### Load ways preprocessing functions (segment_intersecting_ways, etc.)
    logger.info("### LOAD WAYS PREPROCESSING FUNCTIONS ###")
    sgc.load_ways_preprocessing_functions()

    ### Create table with entries of all German municipalities and cities
    logger.info("### FILL municipal_register TABLE ###")
    create_municipal_register()

    logger.info("### DONE ###")


def repair_country_postcodes(country: str = "germany"):
    """Repair postcode/state coverage without requiring state raw_data outputs."""
    regions = _load_regions_config()
    if regions and country not in regions:
        logger.error(f"Invalid country '{country}'. Available countries: {', '.join(regions.keys())}")
        sys.exit(1)

    sgc = DatabaseConstructor()
    logger.info("### CREATE ALL TABLES ###")
    sgc.create_table(table_name="all")
    _refresh_country_postcodes(sgc, country=country, state=None, regions=regions)
    logger.info("### DONE ###")


def main():
    parser = argparse.ArgumentParser(description="Construct pylovo database")
    parser.add_argument("--datapipeline", "-d", action="store_true",
                        help="Use datapipeline output instead of legacy paths")
    parser.add_argument("--repair-postcodes-only", action="store_true",
                        help="Repair postcode/state coverage without loading datapipeline raw data")
    parser.add_argument("--country", "-c", type=str, default="germany",
                        help="Country name (default: germany)")
    parser.add_argument("--state", "-s", type=str, default=None,
                        help="State name (e.g., hamburg, bayern)")

    args = parser.parse_args()

    if args.repair_postcodes_only:
        repair_country_postcodes(country=args.country)
    elif args.datapipeline:
        if not args.state:
            logger.error("--state is required when using --datapipeline")
            return
        main_datapipeline(country=args.country, state=args.state)
    else:
        main_legacy()


if __name__ == "__main__":
    main()
