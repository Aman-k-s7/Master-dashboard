"""
Management command to find and optionally fix anomalous scan records.

Usage:
  # Inspect anomalous records for a device on a date:
  python manage.py fix_anomaly --device CFS02 --date 2025-07-05

  # Also fix (mark is_valid=0) records above a weight threshold:
  python manage.py fix_anomaly --device CFS02 --date 2025-07-05 --threshold 50 --fix
"""
import os

from django.core.management.base import BaseCommand
from django.db import connection
from analytics.services.dashboard import mark_scans_invalid_by_local_date_weight

SCAN_TABLE = os.getenv("WASTE_SCAN_TABLE", "scm_scans")
COMPANY_ID = int(os.getenv("WASTE_COMPANY_ID", "312"))
WEIGHT_MULTIPLIER = float(os.getenv("WASTE_WEIGHT_MULTIPLIER", "100"))


def _computed_weight_expr() -> str:
    json_w = (
        "CASE WHEN JSON_VALID(request) "
        "THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.weight')) "
        "ELSE NULL END"
    )
    return f"COALESCE(NULLIF(CAST({json_w} AS DECIMAL(18,3)), 0), COALESCE(weight, 0) * {WEIGHT_MULTIPLIER})"


class Command(BaseCommand):
    help = "Inspect and optionally fix anomalous scan records"

    def add_arguments(self, parser):
        parser.add_argument("--device", required=True, help="device_serial_no, e.g. CFS02")
        parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
        parser.add_argument(
            "--threshold",
            type=float,
            default=None,
            help="Weight threshold in kg — records above this are flagged as anomalous",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            default=False,
            help="Mark anomalous records as is_valid=0 (requires --threshold)",
        )
        # New: allow fixing by local date + weight (timezone-aware)
        parser.add_argument(
            "--local-date",
            required=False,
            help="Local date in YYYY-MM-DD format (used with --weight and --fix)",
        )
        parser.add_argument(
            "--weight",
            type=float,
            required=False,
            help="Exact computed weight (kg) to mark invalid for the given local date",
        )
        parser.add_argument(
            "--tz",
            default="Asia/Kolkata",
            help="Timezone name for the local date (default: Asia/Kolkata)",
        )

    def handle(self, *args, **options):
        device = options["device"]
        date = options["date"]
        threshold = options["threshold"]
        do_fix = options["fix"]
        local_date = options.get("local_date")
        weight = options.get("weight")
        tz = options.get("tz")

        weight_expr = _computed_weight_expr()

        # --- Inspect all records for this device on this date ---
        select_sql = f"""
            SELECT
                id,
                commodity_name,
                weight                                    AS raw_weight_col,
                CASE WHEN JSON_VALID(request)
                     THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.weight'))
                     ELSE NULL END                        AS json_weight,
                ROUND({weight_expr}, 3)                  AS computed_weight_kg,
                is_valid,
                created_on_date,
                created_at
            FROM `{SCAN_TABLE}`
            WHERE company_id = %s
              AND device_serial_no = %s
              AND created_on_date = %s
            ORDER BY computed_weight_kg DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(select_sql, [COMPANY_ID, device, date])
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

        if not rows:
            self.stdout.write(self.style.WARNING(f"No records found for device={device} date={date}"))
            return

        self.stdout.write(self.style.SUCCESS(f"\nFound {len(rows)} record(s) for {device} on {date}:\n"))
        for row in rows:
            flag = ""
            if threshold and float(row["computed_weight_kg"] or 0) > threshold:
                flag = "  ← ANOMALY"
            self.stdout.write(
                f"  id={row['id']}  commodity={row['commodity_name']}"
                f"  raw_col={row['raw_weight_col']}  json_w={row['json_weight']}"
                f"  computed={row['computed_weight_kg']} kg"
                f"  is_valid={row['is_valid']}{flag}"
            )

        if do_fix:
            if threshold is None:
                self.stderr.write("--threshold is required when using --fix")
                return

            anomalous_ids = [
                row["id"]
                for row in rows
                if float(row["computed_weight_kg"] or 0) > threshold and row["is_valid"] != 0
            ]

            if not anomalous_ids:
                self.stdout.write(self.style.WARNING("\nNo records above threshold to fix."))
                return

            placeholders = ", ".join(["%s"] * len(anomalous_ids))
            update_sql = f"UPDATE `{SCAN_TABLE}` SET is_valid = 0 WHERE id IN ({placeholders})"
            with connection.cursor() as cursor:
                cursor.execute(update_sql, anomalous_ids)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nMarked {len(anomalous_ids)} record(s) as is_valid=0: IDs {anomalous_ids}"
                )
            )

        # New flow: mark by local date + exact weight
        if local_date and weight is not None and do_fix:
            result = mark_scans_invalid_by_local_date_weight(local_date, weight, tz_name=tz)
            if not result.get("success"):
                self.stderr.write(f"Failed to mark scans: {result.get('error')}")
                return
            self.stdout.write(self.style.SUCCESS(f"{result.get('message')} IDs: {result.get('ids')}"))
