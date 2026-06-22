#!/usr/bin/env python3
"""
Extract real postcode polygon boundaries from Geofabrik PBF files.

Replaces GISCO point-centroid approach with actual OSM boundary=postal_code
polygons extracted via osmium + ogr2ogr.

Public API:
    prepare_country(country_id, country_name, nuts2_state_mapping, output_dir,
                    geofabrik_url=None)
"""

import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ERROR: Missing required package: pandas")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PBF_CACHE_DIR = PROJECT_ROOT / "datapipeline" / "cache" / "pbf"


def _download_pbf(url: str) -> Path:
    """Download PBF from Geofabrik with resume support. Returns cached path."""
    PBF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pbf_name = url.split("/")[-1]
    pbf_path = PBF_CACHE_DIR / pbf_name

    if pbf_path.exists():
        size_mb = pbf_path.stat().st_size / 1024 / 1024
        print(f"   [INFO] Using cached PBF: {pbf_name} ({size_mb:.1f} MB)")
        return pbf_path

    import requests

    partial = pbf_path.with_suffix(".pbf.part")
    resume_byte = partial.stat().st_size if partial.exists() else 0
    headers = {}
    if resume_byte > 0:
        headers["Range"] = f"bytes={resume_byte}-"
        print(f"   [DL] Resuming from {resume_byte / 1024 / 1024:.1f} MB...")
    else:
        print(f"   [DL] Downloading PBF...")
    print(f"        {url}")

    r = requests.get(url, timeout=600, stream=True, headers=headers)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0)) + resume_byte
    downloaded = resume_byte
    mode = "ab" if resume_byte > 0 else "wb"

    with open(partial, mode) as f:
        for chunk in r.iter_content(chunk_size=8192 * 16):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                print(
                    f"\r   [{pct:3d}%] {downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB",
                    end="",
                    flush=True,
                )
    print()
    partial.rename(pbf_path)
    print(f"   [OK] Downloaded: {pbf_name} ({downloaded / 1024 / 1024:.1f} MB)")
    return pbf_path


def _extract_postal_boundaries(pbf_path: Path, work_dir: Path) -> Path:
    """Extract boundary=postal_code relations from PBF using osmium."""
    postal_pbf = work_dir / "postal_codes.osm.pbf"
    print("   Extracting postal code boundaries with osmium...")
    subprocess.run(
        [
            "osmium", "tags-filter", str(pbf_path),
            "r/boundary=postal_code",
            "-o", str(postal_pbf), "--overwrite",
        ],
        check=True, capture_output=True,
    )
    size_kb = postal_pbf.stat().st_size / 1024
    print(f"   [OK] Extracted postal codes ({size_kb:.0f} KB)")
    return postal_pbf


def _convert_to_geojson_3035(postal_pbf: Path, work_dir: Path) -> Path:
    """Convert postal PBF to GeoJSON in EPSG:3035."""
    geojson_path = work_dir / "postal_codes_3035.geojson"
    print("   Converting to GeoJSON (EPSG:3035)...")
    subprocess.run(
        [
            "ogr2ogr", "-f", "GeoJSON",
            "-s_srs", "EPSG:4326", "-t_srs", "EPSG:3035",
            str(geojson_path), str(postal_pbf),
            "multipolygons",
        ],
        check=True, capture_output=True,
    )
    return geojson_path


def _multipolygon_to_ewkb_hex(coordinates, srid=3035):
    """Convert GeoJSON MultiPolygon coordinates to EWKB hex string."""
    buf = bytearray()
    buf.append(1)  # little-endian
    buf.extend(struct.pack("<I", 0x20000006))  # MultiPolygon with SRID
    buf.extend(struct.pack("<I", srid))
    buf.extend(struct.pack("<I", len(coordinates)))
    for polygon in coordinates:
        buf.append(1)
        buf.extend(struct.pack("<I", 0x20000003))  # Polygon with SRID
        buf.extend(struct.pack("<I", srid))
        buf.extend(struct.pack("<I", len(polygon)))
        for ring in polygon:
            buf.extend(struct.pack("<I", len(ring)))
            for x, y in ring:
                buf.extend(struct.pack("<dd", x, y))
    return buf.hex().upper()


def _polygon_to_ewkb_hex(coordinates, srid=3035):
    """Convert GeoJSON Polygon to MultiPolygon EWKB hex (wrap in Multi)."""
    return _multipolygon_to_ewkb_hex([coordinates], srid)


def _polygon_area_km2(coordinates):
    """Approximate area in km² using the shoelace formula (EPSG:3035 metres)."""
    total = 0.0
    for polygon in coordinates:
        ring = polygon[0]  # outer ring only
        n = len(ring)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += ring[i][0] * ring[j][1]
            area -= ring[j][0] * ring[i][1]
        total += abs(area) / 2.0
    return total / 1e6


def _parse_postal_code(other_tags: str) -> str:
    """Extract postal_code value from OSM other_tags hstore string."""
    if not other_tags:
        return None
    m = re.search(r'"postal_code"=>"([^"]+)"', other_tags)
    return m.group(1) if m else None


def _parse_geojson_features(geojson_path: Path) -> list:
    """Parse GeoJSON features into list of (plz, ewkb_hex, area_km2) tuples."""
    with open(geojson_path) as f:
        data = json.load(f)

    results = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        geom = feat.get("geometry")
        if not geom:
            continue

        plz = props.get("postal_code") or props.get("ref")
        if not plz:
            plz = _parse_postal_code(props.get("other_tags", ""))
        if not plz:
            # Some features have name like "28279 Bremen"
            name = props.get("name", "")
            m = re.match(r"(\d{4,5})\b", name)
            plz = m.group(1) if m else None
        if not plz:
            continue

        gtype = geom["type"]
        coords = geom["coordinates"]
        if gtype == "MultiPolygon":
            ewkb = _multipolygon_to_ewkb_hex(coords)
            area = _polygon_area_km2(coords)
        elif gtype == "Polygon":
            ewkb = _polygon_to_ewkb_hex(coords)
            area = _polygon_area_km2([coords])
        else:
            continue

        results.append((plz, ewkb, area))

    return results


def extract_postcodes_from_pbf(geofabrik_url: str) -> list:
    """Full extraction pipeline: download PBF → extract postal boundaries → parse.

    Returns:
        List of (plz, ewkb_hex, area_km2) tuples
    """
    pbf_path = _download_pbf(geofabrik_url)

    with tempfile.TemporaryDirectory(prefix="pylovo_postal_") as work_dir:
        work_dir = Path(work_dir)
        postal_pbf = _extract_postal_boundaries(pbf_path, work_dir)
        geojson_path = _convert_to_geojson_3035(postal_pbf, work_dir)
        return _parse_geojson_features(geojson_path)


def _get_state_pbf_urls(country_name: str) -> dict:
    """Get per-state Geofabrik PBF URLs from regions.yaml.

    Returns:
        Dict of state_key → geofabrik_url, or empty dict if states share country PBF.
    """
    import yaml

    regions_path = PROJECT_ROOT / "datapipeline" / "config" / "regions.yaml"
    with open(regions_path) as f:
        regions = yaml.safe_load(f)

    country_lower = country_name.lower().replace(" ", "_")
    country_config = regions.get(country_lower, {})
    country_url = country_config.get("geofabrik_url", "")
    states = country_config.get("states", {})

    if not states:
        return {}

    result = {}
    for state_key, state_data in states.items():
        state_url = state_data.get("geofabrik_url", "")
        if state_url and state_url != country_url:
            result[state_key] = state_url

    return result


def _extract_from_state_pbfs(state_urls: dict) -> tuple:
    """Extract postcodes from per-state PBFs and return combined results with state assignments.

    Returns:
        (postcodes_list, state_assignments_dict) where state_assignments maps plz → state_key
    """
    all_postcodes = {}  # plz → (ewkb, area)
    state_assignments = {}  # plz → state_key

    for state_key, url in sorted(state_urls.items()):
        print(f"\n   --- {state_key} ---")
        state_postcodes = extract_postcodes_from_pbf(url)
        for plz, ewkb, area in state_postcodes:
            if plz not in all_postcodes:
                all_postcodes[plz] = (ewkb, area)
                state_assignments[plz] = state_key
            # If PLZ already seen from another state, keep first occurrence
        print(f"   [OK] {state_key}: {len(state_postcodes)} postcodes")

    postcodes = [(plz, ewkb, area) for plz, (ewkb, area) in all_postcodes.items()]
    return postcodes, state_assignments


def prepare_country(
    country_id: str,
    country_name: str,
    nuts2_state_mapping: dict,
    output_dir: Path,
    geofabrik_url: str = None,
    plz_digits: int = 0,
):
    """Full pipeline: download country PBF, extract postal polygons, save CSV.

    When *geofabrik_url* is explicitly provided the country-level PBF is always
    used (per-state extraction is skipped).  Otherwise, if per-state PBFs exist
    in regions.yaml they are used instead.

    Args:
        country_id: ISO 2-letter code (e.g. 'DE', 'AT')
        country_name: Human-readable name
        nuts2_state_mapping: Dict mapping NUTS2/NUTS1 codes to pylovo state_code
        output_dir: Directory to write output CSV
        geofabrik_url: Country-level Geofabrik PBF URL. If None, read from regions.yaml.
        plz_digits: Zero-pad PLZ to this many digits (e.g. 5 for Germany). 0 = no padding.
    """
    print("=" * 60)
    print(f"{country_name} Data Preparation for Pylovo")
    print("=" * 60)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Output directory: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract postcodes from PBF(s)
    print("\n" + "=" * 60)
    print("Extracting Postcode Polygons from Geofabrik PBF")
    print("=" * 60)

    state_urls = _get_state_pbf_urls(country_name)
    state_assignments = None

    if geofabrik_url:
        # Explicit URL provided — use country-level PBF (skip per-state)
        print(f"   Using country-level PBF...")
        postcodes = extract_postcodes_from_pbf(geofabrik_url)
    elif state_urls:
        # Countries with per-state PBFs: extract from each state individually
        print(f"   Extracting from {len(state_urls)} state PBFs...")
        postcodes, state_assignments = _extract_from_state_pbfs(state_urls)
    else:
        # Look up country URL from regions.yaml
        geofabrik_url = _get_country_geofabrik_url(country_name)
        postcodes = extract_postcodes_from_pbf(geofabrik_url)

    print(f"\n   [OK] Extracted {len(postcodes)} postcode polygons")
    if not postcodes:
        raise ValueError(
            f"No postcode polygons were extracted for {country_name}. "
            "The current Geofabrik/Osmium conversion path did not produce usable multipolygons."
        )

    # Deduplicate: keep the entry with the largest area for each PLZ
    deduped = {}
    for plz, ewkb_hex, area_km2 in postcodes:
        if plz_digits > 0:
            plz = plz.zfill(plz_digits)
        if plz not in deduped or area_km2 > deduped[plz][1]:
            deduped[plz] = (ewkb_hex, area_km2)
    if len(deduped) < len(postcodes):
        print(f"   [INFO] Deduplicated {len(postcodes)} → {len(deduped)} (removed {len(postcodes) - len(deduped)} duplicates)")

    # Step 2: Build DataFrame with state_code assignment
    print("\n" + "=" * 60)
    print(f"Processing {country_name} Postcodes (state_code assignment)")
    print("=" * 60)

    records = []
    for plz, (ewkb_hex, area_km2) in deduped.items():
        sc = state_assignments.get(plz) if state_assignments else None
        records.append({
            "plz": plz,
            "country_code": country_id,
            "state_code": sc,
            "note": f"{plz} {country_name}",
            "qkm": round(area_km2, 2),
            "einwohner": 0,
            "geom": ewkb_hex,
        })

    df = pd.DataFrame(records)

    # If state_codes not yet assigned (single PBF), use spatial intersection
    if not state_assignments:
        _assign_state_codes(df, country_id, country_name, nuts2_state_mapping)

    assigned = df["state_code"].notna().sum()
    print(f"   [OK] Processed {len(df)} postcodes")
    print(f"   [OK] Assigned state_code to {assigned} postcodes")

    if assigned < len(df):
        missing = df[df["state_code"].isna()]
        print(f"   [WARN] {len(missing)} postcodes without state_code: {missing['plz'].tolist()[:20]}")

    print("\n   State distribution:")
    for sc, count in df["state_code"].value_counts().sort_index().items():
        print(f"     {sc}: {count} postcodes")

    # Step 3: Save CSV
    print("\n" + "=" * 60)
    print(f"Saving {country_name} Output Files")
    print("=" * 60)

    df.insert(0, "gid", range(1, len(df) + 1))
    df = df.rename(columns={"einwohner": "einwohner"})  # keep as-is

    country_lower = country_name.lower().replace(" ", "_")
    filename = f"postcode_{country_lower}.csv"
    csv_path = output_dir / filename
    df.to_csv(csv_path, index=False)
    print(f"   [OK] Saved: {csv_path}")
    print(f"     Records: {len(df)}")
    print(f"     With state_code: {assigned}")

    # Done
    print("\n" + "=" * 60)
    print("[OK] DONE!")
    print("=" * 60)
    sample_state = next(iter(nuts2_state_mapping.values()))
    print(f"""
Output files saved to: {output_dir}

Next steps:
1. Run datapipeline for a state:
   make process COUNTRY={country_lower} STATE={sample_state}

2. Load data into database:
   make constructor COUNTRY={country_lower} STATE={sample_state}

3. Generate grids:
   make grid COUNTRY={country_lower} STATE={sample_state} WORKERS=10
""")


def _get_country_geofabrik_url(country_name: str) -> str:
    """Look up the country-level Geofabrik URL from regions.yaml."""
    import yaml

    regions_path = PROJECT_ROOT / "datapipeline" / "config" / "regions.yaml"
    with open(regions_path) as f:
        regions = yaml.safe_load(f)

    country_lower = country_name.lower().replace(" ", "_")
    for key, data in regions.items():
        if key == country_lower:
            return data["geofabrik_url"]

    raise ValueError(f"Country '{country_name}' not found in regions.yaml")


def _assign_state_codes(df: pd.DataFrame, country_id: str, country_name: str,
                        nuts2_state_mapping: dict):
    """Assign state_code to postcodes using spatial intersection with state boundaries.

    Uses the state boundary GeoJSON files that the datapipeline already extracts,
    or falls back to centroid-based NUTS prefix matching.
    """
    import yaml

    regions_path = PROJECT_ROOT / "datapipeline" / "config" / "regions.yaml"
    with open(regions_path) as f:
        regions = yaml.safe_load(f)

    country_lower = country_name.lower().replace(" ", "_")
    country_config = regions.get(country_lower, {})
    states = country_config.get("states", {})

    if not states:
        # Single-state country: assign all to the first (only) state
        if nuts2_state_mapping:
            state_code = next(iter(nuts2_state_mapping.values()))
            df["state_code"] = state_code
        return

    # Try spatial intersection using state boundary GeoJSON files
    boundary_files = {}
    raw_data = PROJECT_ROOT / "raw_data"
    for state_key, state_data in states.items():
        rel_id = state_data.get("osm_relation_id")
        boundary_path = raw_data / country_lower / state_key / "boundaries" / f"{rel_id}_boundary_3035.geojson"
        if boundary_path.exists():
            boundary_files[state_key] = boundary_path

    if boundary_files:
        _assign_by_spatial_intersection(df, boundary_files)
    else:
        # Fallback: assign by NUTS prefix matching from PLZ ranges
        # This is a rough heuristic — spatial intersection is much better
        print("   [INFO] No state boundary files found, using NUTS prefix mapping")
        _assign_by_nuts_mapping(df, nuts2_state_mapping, country_id)


def _assign_by_spatial_intersection(df: pd.DataFrame, boundary_files: dict):
    """Assign state_code by checking which state boundary contains each postcode centroid."""
    from shapely.geometry import shape, MultiPolygon as ShapelyMultiPolygon
    from shapely import prepared

    print(f"   Assigning state_code via spatial intersection ({len(boundary_files)} state boundaries)...")

    state_geoms = {}
    for state_key, path in boundary_files.items():
        with open(path) as f:
            data = json.load(f)
        if data.get("features"):
            # Merge all features into one geometry
            geoms = []
            for feat in data["features"]:
                g = shape(feat["geometry"])
                if g.is_valid:
                    geoms.append(g)
            if geoms:
                from shapely.ops import unary_union
                merged = unary_union(geoms)
                state_geoms[state_key] = prepared.prep(merged)

    # Compute centroids from EWKB hex
    for idx, row in df.iterrows():
        if row["state_code"] is not None:
            continue
        ewkb_hex = row["geom"]
        if not ewkb_hex:
            continue
        centroid = _centroid_from_ewkb_hex(ewkb_hex)
        if centroid is None:
            continue
        from shapely.geometry import Point
        pt = Point(centroid)
        for state_key, prep_geom in state_geoms.items():
            if prep_geom.contains(pt):
                df.at[idx, "state_code"] = state_key
                break


def _centroid_from_ewkb_hex(ewkb_hex: str):
    """Extract approximate centroid (mean of first ring) from EWKB hex MultiPolygon."""
    data = bytes.fromhex(ewkb_hex)
    # Skip: byte_order(1) + type(4) + srid(4) + num_polygons(4) = 13
    offset = 13
    if offset >= len(data):
        return None
    # First polygon: byte_order(1) + type(4) + srid(4) + num_rings(4)
    offset += 13
    if offset >= len(data):
        return None
    num_points = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    sum_x, sum_y = 0.0, 0.0
    for _ in range(min(num_points, 1000)):
        if offset + 16 > len(data):
            break
        x, y = struct.unpack_from("<dd", data, offset)
        sum_x += x
        sum_y += y
        offset += 16
    if num_points > 0:
        return (sum_x / num_points, sum_y / num_points)
    return None


def _assign_by_nuts_mapping(df: pd.DataFrame, nuts2_state_mapping: dict,
                            country_id: str):
    """Fallback: assign all postcodes to states via NUTS mapping.

    When no boundary files are available, assign all to the first matching state.
    This only works well for single-state countries.
    """
    if len(nuts2_state_mapping) == 1:
        state_code = next(iter(nuts2_state_mapping.values()))
        df["state_code"] = state_code
    else:
        print("   [WARN] Multiple states but no boundary files — state_code assignment may be incomplete")
        print("   [HINT] Run the datapipeline for at least one state first to generate boundary files,")
        print("          then re-run prepare_country to get accurate state assignments.")
