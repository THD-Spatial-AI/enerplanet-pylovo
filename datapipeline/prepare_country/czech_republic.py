#!/usr/bin/env python3
"""
Czech Republic postcode preparation for Pylovo.

Uses the RCzechia `zip_codes` GeoPackage, which provides polygon postcode
boundaries. The older Geofabrik/Osmium path currently does not yield usable
postcode polygons for Czech Republic.
"""

import re
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import yaml
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

try:
    from shapely.validation import make_valid
except ImportError:  # pragma: no cover
    make_valid = None

from datapipeline.downloaders.boundaries import BoundaryDownloader
from datapipeline.utils import get_region_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
CZECH_DIR = RAW_DATA_DIR / "czech_republic"
REGIONS_PATH = PROJECT_ROOT / "datapipeline" / "config" / "regions.yaml"

RCZECHIA_ZIP_CODES_URL = "https://rczechia.jla-data.net/zip_codes.gpkg"
RCZECHIA_LAYER = "zip_codes"


def _normalize_plz(value) -> str | None:
    if pd.isna(value):
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    return digits.zfill(5)


def _ensure_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if make_valid is not None and not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom

    polygons = []
    for part in getattr(geom, "geoms", []):
        if isinstance(part, Polygon):
            polygons.append(part)
        elif isinstance(part, MultiPolygon):
            polygons.extend(list(part.geoms))
    if not polygons:
        return None
    return MultiPolygon(polygons)


def _load_rczechia_postcodes() -> gpd.GeoDataFrame:
    print(f"Downloading Czech postcode polygons from RCzechia...")
    print(f"  {RCZECHIA_ZIP_CODES_URL}")

    with tempfile.TemporaryDirectory(prefix="pylovo_cz_postcodes_") as tmpdir:
        gpkg_path = Path(tmpdir) / "zip_codes.gpkg"
        with requests.get(RCZECHIA_ZIP_CODES_URL, timeout=600, stream=True) as response:
            response.raise_for_status()
            with open(gpkg_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

        gdf = gpd.read_file(gpkg_path, layer=RCZECHIA_LAYER)

    print(f"  Loaded {len(gdf)} source features from layer '{RCZECHIA_LAYER}'")
    return gdf


def _filter_current_records(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf.copy()

    if "PLATIOD" in out.columns:
        valid_from = pd.to_datetime(out["PLATIOD"], errors="coerce")
        out = out[valid_from.isna() | (valid_from <= pd.Timestamp.today())].copy()

    if "NEPLATIPO" in out.columns:
        valid_to = pd.to_datetime(out["NEPLATIPO"], errors="coerce")
        out = out[valid_to.isna() | (valid_to >= pd.Timestamp.today())].copy()

    return out


def _load_state_boundary_index() -> gpd.GeoDataFrame | None:
    if not REGIONS_PATH.exists():
        return None

    with open(REGIONS_PATH) as handle:
        regions = yaml.safe_load(handle)

    states = regions.get("czech_republic", {}).get("states", {})
    _ensure_state_boundaries(states)
    records = []
    for state_code, state_data in states.items():
        rel_id = state_data.get("osm_relation_id")
        if not rel_id:
            continue
        boundary_path = (
            RAW_DATA_DIR
            / "czech_republic"
            / state_code
            / "boundaries"
            / f"{rel_id}_boundary_3035.geojson"
        )
        if boundary_path.exists():
            boundary_gdf = gpd.read_file(boundary_path).to_crs("EPSG:3035")
            if boundary_gdf.empty:
                continue
            merged = unary_union(boundary_gdf.geometry.tolist())
            if merged is None or merged.is_empty:
                continue
            records.append({"state_code": state_code, "geometry": merged})

    if not records:
        return None

    return gpd.GeoDataFrame(records, crs="EPSG:3035")


def _ensure_state_boundaries(states: dict) -> None:
    missing = []
    for state_code, state_data in states.items():
        rel_id = state_data.get("osm_relation_id")
        if not rel_id:
            continue
        boundary_path = (
            RAW_DATA_DIR
            / "czech_republic"
            / state_code
            / "boundaries"
            / f"{rel_id}_boundary_3035.geojson"
        )
        if not boundary_path.exists():
            missing.append(state_code)

    if not missing:
        return

    print(f"  Downloading {len(missing)} missing Czech state boundary file(s)...")
    failures = []
    for index, state_code in enumerate(missing, start=1):
        print(f"    [{index}/{len(missing)}] {state_code}")
        try:
            downloader = BoundaryDownloader(get_region_config("czech_republic", state_code))
            boundary_path = downloader.download()
            if not boundary_path.exists():
                failures.append(f"{state_code}: boundary file not created")
                continue
            boundary_gdf = gpd.read_file(boundary_path)
            if boundary_gdf.empty:
                failures.append(f"{state_code}: empty boundary output")
        except Exception as exc:
            failures.append(f"{state_code}: {exc}")

    if failures:
        print("  Warning: some state boundaries could not be prepared:")
        for failure in failures:
            print(f"    - {failure}")


def _assign_state_codes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    boundaries = _load_state_boundary_index()
    out = gdf.copy()
    out["state_code"] = None

    if boundaries is None or boundaries.empty:
        print("  No local state boundary files found; leaving state_code empty for now")
        return out

    if out.crs is not None and out.crs != boundaries.crs:
        out = out.to_crs(boundaries.crs)

    postcode_parts = out[["plz", "geometry"]].reset_index(drop=True).copy()
    postcode_parts["postcode_row_id"] = postcode_parts.index

    try:
        joined = gpd.overlay(
            postcode_parts,
            boundaries[["state_code", "geometry"]],
            how="intersection",
            keep_geom_type=False,
        )
    except Exception as exc:
        print(f"  Warning: polygon overlap assignment failed ({exc}); falling back to representative-point assignment")
        points = out[["plz", "geometry"]].copy()
        points.geometry = points.geometry.representative_point()
        joined = gpd.sjoin(points, boundaries[["state_code", "geometry"]], how="left", predicate="within")
        state_map = (
            joined.dropna(subset=["state_code"])
            .drop_duplicates(subset=["plz"])
            .set_index("plz")["state_code"]
        )
        out["state_code"] = out["plz"].map(state_map)
        assigned = out["state_code"].notna().sum()
        print(f"  Assigned state_code for {assigned}/{len(out)} postcodes from prepared state boundary files")
        return out

    if joined.empty:
        print("  Warning: postcode/state polygon overlap produced no matches; leaving state_code empty")
        return out

    joined["overlap_area"] = joined.geometry.area
    best_matches = (
        joined.sort_values(["postcode_row_id", "overlap_area"], ascending=[True, False])
        .drop_duplicates(subset=["postcode_row_id"], keep="first")
        .set_index("postcode_row_id")["state_code"]
    )
    out.loc[best_matches.index, "state_code"] = best_matches.values

    assigned = out["state_code"].notna().sum()
    print(f"  Assigned state_code for {assigned}/{len(out)} postcodes from prepared state boundary files")
    return out


def _prepare_postcodes() -> gpd.GeoDataFrame:
    gdf = _filter_current_records(_load_rczechia_postcodes())

    if "PSC" not in gdf.columns:
        raise ValueError("RCzechia postcode layer is missing expected 'PSC' column")

    gdf = gdf.rename(columns={"PSC": "plz", "NAZ_POSTA": "post_name"})
    gdf["plz"] = gdf["plz"].map(_normalize_plz)
    gdf = gdf.dropna(subset=["plz", "geometry"]).copy()

    gdf["geometry"] = gdf.geometry.map(_ensure_multipolygon)
    gdf = gdf.dropna(subset=["geometry"]).copy()
    gdf = gdf.to_crs("EPSG:3035")

    if "post_name" in gdf.columns:
        gdf["post_name"] = gdf["post_name"].fillna("").astype(str).str.strip()
    else:
        gdf["post_name"] = ""

    gdf["note"] = gdf["plz"] + " " + gdf["post_name"].where(gdf["post_name"] != "", "Czech Republic")
    gdf = gdf[["plz", "note", "geometry"]]

    gdf = gdf.dissolve(by="plz", aggfunc={"note": "first"}, as_index=False)
    gdf["geometry"] = gdf.geometry.map(_ensure_multipolygon)
    gdf = gdf.dropna(subset=["geometry"]).copy()

    geom_types = gdf.geometry.geom_type.value_counts().to_dict()
    print(f"  Dissolved to {len(gdf)} unique postcode polygons")
    print(f"  Geometry types after dissolve: {geom_types}")

    return _assign_state_codes(gdf)


def _write_outputs(gdf: gpd.GeoDataFrame) -> None:
    CZECH_DIR.mkdir(parents=True, exist_ok=True)

    geojson_path = CZECH_DIR / "postcodes.geojson"
    gdf.to_file(geojson_path, driver="GeoJSON")

    records = []
    for idx, row in gdf.iterrows():
        records.append(
            {
                "gid": idx + 1,
                "plz": row["plz"],
                "state_code": row.get("state_code"),
                "note": row["note"],
                "qkm": round(row.geometry.area / 1_000_000, 6),
                "einwohner": 0,
                "geom": row.geometry.wkb_hex,
            }
        )

    df = pd.DataFrame(records)

    country_csv_path = CZECH_DIR / "postcode_czech_republic.csv"
    generic_csv_path = CZECH_DIR / "postcode.csv"
    df.to_csv(country_csv_path, index=False)
    df.to_csv(generic_csv_path, index=False)

    assigned = int(df["state_code"].notna().sum()) if "state_code" in df.columns else 0

    print(f"Saved GeoJSON: {geojson_path}")
    print(f"Saved CSV: {country_csv_path}")
    print(f"Saved CSV: {generic_csv_path}")
    print(f"  Records: {len(df)}")
    print(f"  With state_code: {assigned}")


def main():
    print("=" * 60)
    print("PREPARING CZECH REPUBLIC POSTCODE DATA")
    print("=" * 60)
    try:
        gdf = _prepare_postcodes()
        if gdf.empty:
            raise ValueError("Prepared Czech postcode dataset is empty")
        _write_outputs(gdf)
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("CZECH REPUBLIC DATA PREPARATION COMPLETE")
    print("=" * 60)
    print(
        f"""
Output files saved to: {CZECH_DIR}

Next steps:
1. Run datapipeline:
   make datapipeline COUNTRY=czech_republic STATE=praha

2. Load data into database:
   make constructor COUNTRY=czech_republic STATE=praha

3. Generate grids:
   make grid COUNTRY=czech_republic STATE=praha WORKERS=10
"""
    )


if __name__ == "__main__":
    main()
