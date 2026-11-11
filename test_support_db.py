
from backend.history import get_connection, get_report_support_count

conn = get_connection()

rows = conn.execute("""
    SELECT report_id, citizen_id, created_at
    FROM report_supports
""").fetchall()

print("Support records:", rows)

print(
    "RR-2026-00009 support count:",
    get_report_support_count("RR-2026-00009")
)

conn.close()
