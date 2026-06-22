"""
Delete state-scoped data from the database.

Examples:
  python runme/delete/delete_state.py --country germany --state bayern --dry-run
  python runme/delete/delete_state.py --country germany --state bayern --execute
"""

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import get_country_code  # noqa: E402
from src.database.database_client import DatabaseClient  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Delete data for a country/state scope")
    parser.add_argument("--country", required=True, help="Country name (e.g. germany) or ISO code (e.g. DE)")
    parser.add_argument("--state", required=True, help="State code/name (e.g. bayern)")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute deletion (default is dry-run preview only)",
    )
    parser.add_argument(
        "--drop-state-row",
        action="store_true",
        help="Also delete the state row from state table after data deletion",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run preview (takes precedence over --execute)",
    )
    args = parser.parse_args()

    country_input = args.country.strip()
    country_code = get_country_code(country_input.lower()) if len(country_input) != 2 else country_input.upper()
    state_input = args.state.strip()

    dry_run = True
    if args.execute:
        dry_run = False
    if args.dry_run:
        dry_run = True

    with DatabaseClient() as dbc:
        result = dbc.delete_state_data(
            country=country_code,
            state_code=state_input,
            dry_run=dry_run,
            drop_state_row=args.drop_state_row,
        )

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"[{mode}] country={result['country_code']} state={result['state_code']}")
    print(f"Impact: {result['impact']}")
    if dry_run:
        print("No rows deleted (preview only).")
    else:
        print(f"Deleted: {result['deleted']}")


if __name__ == "__main__":
    main()
