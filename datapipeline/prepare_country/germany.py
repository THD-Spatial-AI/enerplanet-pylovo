#!/usr/bin/env python3
"""
Germany Data Preparation Script for Pylovo

Extracts real postcode polygon boundaries from Geofabrik PBF data
with NUTS1→Bundesland state assignment.

Usage:
    python -m datapipeline.prepare_country germany
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datapipeline.prepare_country.geofabrik_postcodes import prepare_country

RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
GERMANY_DIR = RAW_DATA_DIR / "germany"

# GADM NAME_1 / NUTS1 → pylovo state_code mapping
NUTS_STATE_MAPPING = {
    "DE1": "baden_wuerttemberg",
    "DE2": "bayern",
    "DE3": "berlin",
    "DE4": "brandenburg",
    "DE5": "bremen",
    "DE6": "hamburg",
    "DE7": "hessen",
    "DE8": "mecklenburg_vorpommern",
    "DE9": "niedersachsen",
    "DEA": "nordrhein_westfalen",
    "DEB": "rheinland_pfalz",
    "DEC": "saarland",
    "DED": "sachsen",
    "DEE": "sachsen_anhalt",
    "DEF": "schleswig_holstein",
    "DEG": "thueringen",
}

def main():
    try:
        prepare_country(
            country_id="DE",
            country_name="Germany",
            nuts2_state_mapping=NUTS_STATE_MAPPING,
            output_dir=GERMANY_DIR,
            plz_digits=5,
        )
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
