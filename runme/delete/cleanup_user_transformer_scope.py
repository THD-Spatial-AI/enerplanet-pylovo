"""
One-time cleanup for legacy unscoped USER transformer data.

Default mode is DRY-RUN (preview only). Use --execute to apply changes.

What it cleans:
1. USER grids (grid_result.plz='USER') with missing scope:
   - empty user_id
   - AND/OR both model_id + draft_id empty
2. Orphan USER grids without transformer_positions rows.
3. building_transformer_assignments with missing scope:
   - empty user_id
   - AND/OR both model_id + draft_id empty
4. Orphan building_transformer_assignments pointing to missing grid_result.

Safety:
- By default, USER grids that still have rows in buildings_result are NOT deleted.
  Use --force-delete-grids-with-buildings to override (risky).
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2 as psy


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_env_defaults():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return 1
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)
    except Exception:
        # Non-fatal; environment variables can still be provided externally.
        pass


_load_env_defaults()

DBNAME = os.getenv("DBNAME", "pylovo_db")
DBUSER = os.getenv("DBUSER", "postgres")
PASSWORD = os.getenv("PASSWORD", "postgres")
HOST = os.getenv("HOST", "localhost")
PORT = os.getenv("PORT", "5432")
TARGET_SCHEMA = os.getenv("TARGET_SCHEMA", "public")


def _sample(values: list[int], limit: int) -> list[int]:
    if limit <= 0:
        return []
    return values[:limit]


def _count_rows_for_grid_ids(cur, table_name: str, grid_ids: list[int]) -> int:
    if not grid_ids:
        return 0
    cur.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE grid_result_id = ANY(%s);",
        (grid_ids,),
    )
    return int(cur.fetchone()[0] or 0)


def _connect():
    return psy.connect(
        database=DBNAME,
        user=DBUSER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        options=f"-c search_path={TARGET_SCHEMA},public",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup legacy unscoped USER transformers and assignments."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute deletion (default is dry-run preview only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run preview (takes precedence over --execute).",
    )
    parser.add_argument(
        "--version-id",
        default="1",
        help="Version ID scope for USER grid cleanup (default: 1).",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="How many IDs to print per category (default: 20).",
    )
    parser.add_argument(
        "--force-delete-grids-with-buildings",
        action="store_true",
        help="Also delete USER grids even if they still have buildings_result rows (risky).",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run ANALYZE on affected tables after execute.",
    )
    args = parser.parse_args()

    dry_run = True
    if args.execute:
        dry_run = False
    if args.dry_run:
        dry_run = True

    try:
        conn = _connect()
    except psy.OperationalError as exc:
        print("[ERROR] Failed to connect to PostgreSQL.")
        print(f"        host={HOST} port={PORT} db={DBNAME} user={DBUSER}")
        if str(exc).strip():
            print(f"        details: {exc}")
        print("        Tip: override env vars, e.g. HOST=localhost PORT=5433")
        return 1

    with conn:
        cur = conn.cursor()

        # Table existence guards.
        cur.execute("SELECT to_regclass('public.grid_result');")
        if cur.fetchone()[0] is None:
            print("[ERROR] Table grid_result not found.")
            return 1

        # Backward-compatible schema guards.
        cur.execute("ALTER TABLE grid_result ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);")
        cur.execute("ALTER TABLE grid_result ADD COLUMN IF NOT EXISTS model_id INTEGER;")
        cur.execute("ALTER TABLE grid_result ADD COLUMN IF NOT EXISTS draft_id VARCHAR(255);")

        cur.execute("SELECT to_regclass('public.building_transformer_assignments');")
        bta_exists = cur.fetchone()[0] is not None
        if bta_exists:
            cur.execute("ALTER TABLE building_transformer_assignments ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);")
            cur.execute("ALTER TABLE building_transformer_assignments ADD COLUMN IF NOT EXISTS model_id INTEGER;")
            cur.execute("ALTER TABLE building_transformer_assignments ADD COLUMN IF NOT EXISTS draft_id VARCHAR(255);")

        # 1) USER grids with missing scope.
        cur.execute(
            """
            SELECT gr.grid_result_id
            FROM grid_result gr
            WHERE gr.version_id = %s
              AND gr.plz = 'USER'
              AND (
                    COALESCE(BTRIM(gr.user_id), '') = ''
                    OR (
                        gr.model_id IS NULL
                        AND COALESCE(BTRIM(gr.draft_id), '') = ''
                    )
                  )
            ORDER BY gr.grid_result_id;
            """,
            (args.version_id,),
        )
        unscoped_user_grid_ids = [int(row[0]) for row in cur.fetchall()]

        # 2) USER grids without transformer_positions.
        cur.execute(
            """
            SELECT gr.grid_result_id
            FROM grid_result gr
            LEFT JOIN transformer_positions tp
              ON tp.grid_result_id = gr.grid_result_id
            WHERE gr.version_id = %s
              AND gr.plz = 'USER'
              AND tp.grid_result_id IS NULL
            ORDER BY gr.grid_result_id;
            """,
            (args.version_id,),
        )
        orphan_user_grid_ids = [int(row[0]) for row in cur.fetchall()]

        candidate_grid_ids = sorted(set(unscoped_user_grid_ids) | set(orphan_user_grid_ids))

        # Safety guard: keep grids that still have buildings_result rows unless forced.
        protected_grid_ids: list[int] = []
        if candidate_grid_ids:
            cur.execute(
                """
                SELECT br.grid_result_id
                FROM buildings_result br
                WHERE br.version_id = %s
                  AND br.grid_result_id = ANY(%s)
                GROUP BY br.grid_result_id
                ORDER BY br.grid_result_id;
                """,
                (args.version_id, candidate_grid_ids),
            )
            protected_grid_ids = [int(row[0]) for row in cur.fetchall()]

        if args.force_delete_grids_with_buildings:
            grid_ids_to_delete = candidate_grid_ids
        else:
            protected_set = set(protected_grid_ids)
            grid_ids_to_delete = [gid for gid in candidate_grid_ids if gid not in protected_set]

        # 3/4) Assignment cleanup.
        unscoped_bta_ids: list[int] = []
        orphan_bta_ids: list[int] = []
        bta_ids_to_delete: list[int] = []
        if bta_exists:
            cur.execute(
                """
                SELECT bta.assignment_id
                FROM building_transformer_assignments bta
                WHERE
                    COALESCE(BTRIM(bta.user_id), '') = ''
                    OR (
                        bta.model_id IS NULL
                        AND COALESCE(BTRIM(bta.draft_id), '') = ''
                    )
                ORDER BY bta.assignment_id;
                """
            )
            unscoped_bta_ids = [int(row[0]) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT bta.assignment_id
                FROM building_transformer_assignments bta
                LEFT JOIN grid_result gr
                  ON gr.grid_result_id = bta.grid_result_id
                WHERE gr.grid_result_id IS NULL
                ORDER BY bta.assignment_id;
                """
            )
            orphan_bta_ids = [int(row[0]) for row in cur.fetchall()]

            bta_ids_to_delete = sorted(set(unscoped_bta_ids) | set(orphan_bta_ids))

        # Report.
        mode = "DRY-RUN" if dry_run else "EXECUTE"
        print(f"[{mode}] Legacy USER scope cleanup")
        print(f"version_id: {args.version_id}")
        print("")
        print(f"unscoped_user_grid_ids: {len(unscoped_user_grid_ids)}")
        if unscoped_user_grid_ids:
            print(f"  sample: {_sample(unscoped_user_grid_ids, args.sample_limit)}")
        print(f"orphan_user_grid_ids: {len(orphan_user_grid_ids)}")
        if orphan_user_grid_ids:
            print(f"  sample: {_sample(orphan_user_grid_ids, args.sample_limit)}")
        print(f"candidate_user_grid_ids: {len(candidate_grid_ids)}")
        if candidate_grid_ids:
            print(f"  sample: {_sample(candidate_grid_ids, args.sample_limit)}")
        print(f"protected_user_grid_ids_with_buildings: {len(protected_grid_ids)}")
        if protected_grid_ids:
            print(f"  sample: {_sample(protected_grid_ids, args.sample_limit)}")
        print(f"user_grid_ids_to_delete: {len(grid_ids_to_delete)}")
        if grid_ids_to_delete:
            print(f"  sample: {_sample(grid_ids_to_delete, args.sample_limit)}")
        print("")
        if bta_exists:
            print(f"unscoped_bta_ids: {len(unscoped_bta_ids)}")
            if unscoped_bta_ids:
                print(f"  sample: {_sample(unscoped_bta_ids, args.sample_limit)}")
            print(f"orphan_bta_ids: {len(orphan_bta_ids)}")
            if orphan_bta_ids:
                print(f"  sample: {_sample(orphan_bta_ids, args.sample_limit)}")
            print(f"bta_ids_to_delete: {len(bta_ids_to_delete)}")
            if bta_ids_to_delete:
                print(f"  sample: {_sample(bta_ids_to_delete, args.sample_limit)}")
        else:
            print("building_transformer_assignments table not found (skipped)")

        print("")
        print(
            "dependent_rows_for_user_grids_to_delete:"
            f" tp={_count_rows_for_grid_ids(cur, 'transformer_positions', grid_ids_to_delete)}"
            f", lr={_count_rows_for_grid_ids(cur, 'lines_result', grid_ids_to_delete)}"
            + (
                f", bta={_count_rows_for_grid_ids(cur, 'building_transformer_assignments', grid_ids_to_delete)}"
                if bta_exists
                else ""
            )
        )

        if dry_run:
            print("")
            print("No rows deleted (preview only).")
            if protected_grid_ids and not args.force_delete_grids_with_buildings:
                print(
                    "Note: Some candidate USER grids were protected because they still have buildings_result rows."
                )
                print("      Re-run with --force-delete-grids-with-buildings only if you are sure.")
            return 0

        deleted_grid_rows = 0
        deleted_bta_rows = 0

        try:
            if bta_exists and bta_ids_to_delete:
                cur.execute(
                    """
                    DELETE FROM building_transformer_assignments
                    WHERE assignment_id = ANY(%s);
                    """,
                    (bta_ids_to_delete,),
                )
                deleted_bta_rows += int(cur.rowcount or 0)

            if grid_ids_to_delete:
                cur.execute(
                    """
                    DELETE FROM grid_result
                    WHERE version_id = %s
                      AND plz = 'USER'
                      AND grid_result_id = ANY(%s);
                    """,
                    (args.version_id, grid_ids_to_delete),
                )
                deleted_grid_rows += int(cur.rowcount or 0)

            if args.analyze and (deleted_grid_rows > 0 or deleted_bta_rows > 0):
                cur.execute("ANALYZE grid_result;")
                cur.execute("ANALYZE transformer_positions;")
                cur.execute("ANALYZE lines_result;")
                if bta_exists:
                    cur.execute("ANALYZE building_transformer_assignments;")

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        print("")
        print("Cleanup executed.")
        print(f"deleted_grid_result_rows: {deleted_grid_rows}")
        print(f"deleted_bta_rows: {deleted_bta_rows}")
        if args.analyze and (deleted_grid_rows > 0 or deleted_bta_rows > 0):
            print("ANALYZE completed on affected tables.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
