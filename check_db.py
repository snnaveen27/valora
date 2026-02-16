import sqlite3

conn = sqlite3.connect('storage/database/valora.db')
cursor = conn.cursor()

# Check all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for t in tables:
    print(f'  {t[0]}')

# Check places table if it exists
if any('places' in t[0] for t in tables):
    cursor.execute('SELECT COUNT(*) FROM places')
    count = cursor.fetchone()[0]
    print(f'\nPlaces table has {count} rows')
    if count > 0:
        # Get column names first
        cursor.execute('PRAGMA table_info(places)')
        columns = [col[1] for col in cursor.fetchall()]
        print(f'Places columns: {columns}')
        
        # Try to get some data
        cursor.execute(f'SELECT * FROM places LIMIT 3')
        rows = cursor.fetchall()
        print('Sample places:')
        for r in rows:
            print(f'  {r}')

# Check transport_stops table (it's named transport_stops, not transport)
if any('transport_stops' in t[0] for t in tables):
    cursor.execute('SELECT COUNT(*) FROM transport_stops')
    count = cursor.fetchone()[0]
    print(f'\nTransport_stops table has {count} rows')
    if count > 0:
        cursor.execute('SELECT name, latitude, longitude FROM transport_stops LIMIT 3')
        rows = cursor.fetchall()
        print('Sample transport:')
        for r in rows:
            print(f'  {r[0]} at {r[1]}, {r[2]}')

# Check for Whitefield specifically
cursor.execute("SELECT name, center_latitude, center_longitude FROM places WHERE LOWER(name) LIKE '%whitefield%'")
whitefield_places = cursor.fetchall()
print(f'\nWhitefield in places table: {len(whitefield_places)}')
for w in whitefield_places:
    print(f'  {w[0]} at {w[1]}, {w[2]}')

# Also check what the query service returns
print('\n--- Testing query service ---')
try:
    from database.query_service import get_query_service
    db = get_query_service()
    places = db.get_all_places()
    whitefield_in_qs = [p for p in places if 'whitefield' in p['name'].lower()]
    print(f'Whitefield in query service: {len(whitefield_in_qs)}')
    if whitefield_in_qs:
        print(f'First: {whitefield_in_qs[0]}')
except Exception as e:
    print(f'Error: {e}')

conn.close()
