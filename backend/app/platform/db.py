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
        versions={r['version'] for r in c.execute('SELECT version FROM schema_migrations').fetchall()} if exists else set()
        for path in sorted(Path('migrations').glob('[0-9]*.sql')):
            version=int(path.name.split('_')[0])
            if version not in versions:c.execute(path.read_text())

if __name__=='__main__': migrate()
