"""One-time copy of the old SQLite demo database into MySQL, keeping every ID.

Run from the project folder:  .venv/bin/python scripts/migrate_sqlite_to_mysql.py [--sqlite data/hypecheck.sqlite3] [--replace]

Refuses to touch a MySQL database that already has HypeCheck tables unless --replace is given.
"""
import argparse
from decimal import Decimal
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402  (reads .env for the MySQL settings)

MONEY_COLUMNS = {'estimated_price', 'amount', 'budget_amount'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', default=str(server.ROOT / 'data' / 'hypecheck.sqlite3'))
    parser.add_argument('--replace', action='store_true', help='drop existing HypeCheck tables in MySQL first')
    args = parser.parse_args()

    source = Path(args.sqlite)
    if not source.exists():
        sys.exit(f'No SQLite database at {source}')
    old = sqlite3.connect(source)
    old.row_factory = sqlite3.Row

    db = server.connect()
    try:
        if server.tables_exist(db):
            if not args.replace:
                sys.exit(f'MySQL database "{server.DB["database"]}" already has HypeCheck tables. Use --replace to overwrite.')
            server.q(db, 'SET FOREIGN_KEY_CHECKS = 0')
            for table in ['sessions', 'login_attempts', *server.TABLES]:
                server.q(db, f'DROP TABLE IF EXISTS {table}')
            server.q(db, 'SET FOREIGN_KEY_CHECKS = 1')
        for statement in server.statements((server.ROOT / 'schema.sql').read_text()):
            server.q(db, statement)
        copied = {}
        for table in server.TABLES:  # parents before children, so every foreign key already exists
            rows = old.execute(f'SELECT * FROM {table}').fetchall()
            for row in rows:
                columns = list(row.keys())
                values = [str(Decimal(str(row[c])).quantize(Decimal('.01'))) if c in MONEY_COLUMNS and row[c] is not None else row[c] for c in columns]
                server.q(db, f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({", ".join(["%s"] * len(columns))})', values)
            copied[table] = len(rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        old.close()
    for table, count in copied.items():
        print(f'{table}: {count} rows')
    print(f'Copied into MySQL database "{server.DB["database"]}".')


if __name__ == '__main__':
    main()
