import sqlite3

def main():
    conn = sqlite3.connect('ev_fleet.db')
    c = conn.cursor()
    print("Telemetry sample:")
    c.execute("""
        select datetime, speed, battery_pct, odometer_distance, working_status, is_charging, income 
        from telemetry 
        where driver_id = 'D001' 
        order by datetime asc 
        limit 10
    """)
    for r in c.fetchall():
        print(r)

    print("\nDistinct driver IDs:")
    c.execute("select distinct driver_id from telemetry")
    print(c.fetchall())

if __name__ == '__main__':
    main()
