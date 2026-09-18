import sqlite3
import csv
import os
import datetime

db_path = "e:/scada/backend/microgrid.db"
export_path_root = "e:/scada/grid_exports_dataset.csv"
export_path_sample = "e:/scada/sample_datasets/grid_exports_dataset.csv"

def export_data():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Fetching grid export records (grid_power < 0)...")
    # Fetch all records where grid_power < 0 (meaning power is exported to the grid)
    cursor.execute("SELECT * FROM scada_historian WHERE grid_power < 0 ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No grid export records found in the database.")
        return

    print(f"Found {len(rows)} records. Writing to CSV files...")
    
    # Write to both the workspace root and the sample_datasets directory
    for export_path in [export_path_root, export_path_sample]:
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            # Add a human-readable 'datetime' column followed by all original telemetry columns
            headers = ['datetime'] + [col for col in rows[0].keys()]
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for row in rows:
                row_dict = dict(row)
                epoch = row_dict['timestamp']
                # Convert the unix timestamp to local datetime string
                dt_str = datetime.datetime.fromtimestamp(epoch).strftime('%Y-%m-%d %H:%M:%S')
                
                # Write row data
                line = [dt_str] + [row_dict[col] for col in rows[0].keys()]
                writer.writerow(line)
                
        print(f"Exported successfully to: {export_path}")

if __name__ == "__main__":
    export_data()
