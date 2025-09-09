import sqlite3
from datetime import datetime

DB_FILE = "forecast.db"  # shared DB with forecasting app

# ✅ Step 1: Create QC log table (no BWO, uses project + builder + lot)
def create_qc_log_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS qc_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            builder TEXT NOT NULL,
            lot_number TEXT NOT NULL,
            install_date TEXT NOT NULL,
            submitted_by TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ qc_log table ready (project + builder + lot_number)")


# ✅ Step 2: Save a new QC submission (from QC app form)
def save_qc_entry(project, builder, lot_number, install_date, submitted_by=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO qc_log (project, builder, lot_number, install_date, submitted_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (project, builder, lot_number, install_date, submitted_by))
    conn.commit()
    conn.close()
    print(f"✅ Saved QC entry for {project} / {builder} / Lot {lot_number} → {install_date}")


# ✅ Step 3: Sync install dates into Forecast_Log based on project + builder + lot match
def sync_qc_to_forecast(project, builder, lot_number, insall_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get latest installs from QC log
    c.execute("SELECT project, builder, lot_number, install_date FROM qc_log")
    qc_data = c.fetchall()

    updated = 0
    for project, builder, lot_number, install_date in qc_data:
        c.execute('''
            UPDATE Forecast_Log
            SET actual_install = ?
            WHERE project = ? AND builder = ? AND lot_number = ?
              AND (actual_install IS NULL OR actual_install != ?)
        ''', (install_date, project, builder, lot_number, install_date))

        if c.rowcount:
            updated += 1

    conn.commit()
    conn.close()
    print(f"♻️ Synced {updated} install dates from QC app to Forecast_Log")


if __name__ == "__main__":
    create_qc_log_table()

    # Example test submission:
    # save_qc_entry("TESORO", "LENNAR", "57", "2025-09-06", "Installer Joe")

    # Manual sync run:
    sync_qc_to_forecast()

