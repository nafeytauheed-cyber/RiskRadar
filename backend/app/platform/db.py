import os
from pathlib import Path
import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=3)


def migrate():
    with connect() as c:
        c.execute('SELECT pg_advisory_xact_lock(18440218)')
        exists=c.execute("SELECT to_regclass('schema_migrations') AS name").fetchone()['name']
        if exists and c.execute('SELECT 1 FROM schema_migrations WHERE version=1').fetchone():
            return
        c.execute(Path('migrations/001_platform.sql').read_text())

if __name__=='__main__': migrate()
