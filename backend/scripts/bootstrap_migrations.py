"""Stamp legacy databases and apply pending Alembic migrations."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url)
    insp = inspect(engine)
    tables = insp.get_table_names()

    version = None
    if "alembic_version" in tables:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            version = row[0] if row else None

    product_columns = {col["name"] for col in insp.get_columns("products")} if "products" in tables else set()

    if version is None and "products" in tables:
        print("Legacy schema detected; stamping 0001_initial before upgrade.")
        subprocess.check_call([sys.executable, "-m", "alembic", "-c", "/app/alembic.ini", "stamp", "0001_initial"])
    elif version == "0001_initial" and "owner_id" in product_columns:
        print("Schema already migrated; stamping head.")
        subprocess.check_call(
            [sys.executable, "-m", "alembic", "-c", "/app/alembic.ini", "stamp", "0002_multi_tenant_auth"]
        )
        return

    subprocess.check_call([sys.executable, "-m", "alembic", "-c", "/app/alembic.ini", "upgrade", "head"])


if __name__ == "__main__":
    main()
