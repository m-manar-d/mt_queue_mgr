### Changes in V4:
- Implemented multi-threading.
- Migrated the database from SQLite to mySQL.
- Export csv of Limiter Routers with credentials.
- Batch add limiter routers from csv.
- Logger added.
- Better exception handling and logging.
- Some bug fixes applied.
- Code optimizations, and linting

### Changes in V3:
- Exception handling.
- Hide Routers passwords.
- Updated versions of Django/Gunicorn and Python.
- Some bug fixes applied.
- Code revision/linting

### Changes in V2:

- Ability to define multiple groups of limiter routers (each group will synchronize separately but duplicate simple queue names are not allowed).
- Updated versions of Django/Gunicorn and Python.
- Some bug fixes applied.