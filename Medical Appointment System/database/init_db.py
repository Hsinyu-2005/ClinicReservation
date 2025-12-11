import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "instance", "clinic.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def get_schedules():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM outpatient_schedules").fetchall()
    conn.close()
    return rows

def book_schedule(schedule_id, member_id):
    conn = get_conn()
    cur = conn.cursor()

    # 名額判斷
    cur.execute("SELECT remaining_quota FROM outpatient_schedules WHERE id=?", (schedule_id,))
    remain = cur.fetchone()[0]

    if remain <= 0:
        conn.close()
        return False

    # 新增預約
    cur.execute("""
        INSERT INTO appointment_records (schedule_id, member_id, status)
        VALUES (?, ?, ?)
    """, (schedule_id, member_id, "Success"))

    # 扣除名額
    cur.execute("""
        UPDATE outpatient_schedules
        SET remaining_quota = remaining_quota - 1
        WHERE id=?
    """, (schedule_id,))

    conn.commit()
    conn.close()
    return True

def get_my_appointments(member_id):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT a.*, s.department, s.doctor_name, s.date, s.time_slot
        FROM appointment_records a
        JOIN outpatient_schedules s ON a.schedule_id = s.id
        WHERE a.member_id=?
    """, (member_id,)).fetchall()
    conn.close()
    return rows
