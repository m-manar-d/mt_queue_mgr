import sqlite3

conn = sqlite3.connect('db.sqlite3', isolation_level=None)
conn.execute('pragma journal_mode=wal')
