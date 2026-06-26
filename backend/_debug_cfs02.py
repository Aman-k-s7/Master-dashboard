import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "waste_dashboard_backend.settings")
django.setup()

from django.db import connection

table = os.getenv("WASTE_SCAN_TABLE", "scm_scans")
company = int(os.getenv("WASTE_COMPANY_ID", "312"))

with connection.cursor() as c:
    # All scans for CFS02 on May 5
    c.execute(
        f"SELECT id, device_serial_no, is_valid, commodity_name, weight, created_on_date, "
        f"CASE WHEN JSON_VALID(request) THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.weight')) ELSE NULL END AS req_weight, "
        f"CASE WHEN JSON_VALID(request) THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.day_part')) ELSE NULL END AS day_part, "
        f"CASE WHEN JSON_VALID(request) THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.food_waste_type')) ELSE NULL END AS waste_type "
        f"FROM `{table}` WHERE company_id = %s AND device_serial_no = 'CFS02' AND created_on_date = '2026-05-05' ORDER BY id",
        [company]
    )
    cols = [d[0] for d in c.description]
    rows = c.fetchall()

    lines = [f"Total rows on 2026-05-05 for CFS02: {len(rows)}", ""]
    for row in rows:
        lines.append(str(dict(zip(cols, row))))

    # Also total count with and without is_valid
    c.execute(
        f"SELECT COUNT(*) FROM `{table}` WHERE company_id = %s AND is_valid = 1 "
        f"AND commodity_name IS NOT NULL AND created_on_date IS NOT NULL",
        [company]
    )
    lines.append(f"\nTotal scans (all devices, is_valid=1, has commodity+date): {c.fetchone()[0]}")

    c.execute(
        f"SELECT COUNT(*) FROM `{table}` WHERE company_id = %s "
        f"AND commodity_name IS NOT NULL AND created_on_date IS NOT NULL",
        [company]
    )
    lines.append(f"Total scans (all devices, NO is_valid filter): {c.fetchone()[0]}")

output = "\n".join(lines)
print(output)

with open("_debug_output.txt", "w") as f:
    f.write(output)

print("\nOutput also saved to _debug_output.txt")
