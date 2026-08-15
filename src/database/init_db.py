"""
src/database/init_db.py — Database initialisation and session factory.
Run directly to create tables and seed the transformer fleet.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Transformer
from config import DATABASE_URL, TRANSFORMER_FLEET

engine  = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


def get_session():
    """Return a new DB session (caller must close it)."""
    return Session()


def init_db():
    """Create all tables and seed the transformer fleet if not already present."""
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        existing_ids = {t.id for t in session.query(Transformer).all()}
        added = 0
        for cfg in TRANSFORMER_FLEET:
            if cfg["id"] not in existing_ids:
                session.add(Transformer(
                    id                      = cfg["id"],
                    name                    = cfg["name"],
                    zone                    = cfg["zone"],
                    type                    = cfg["type"],
                    rated_kva               = cfg["rated_kva"],
                    rated_voltage_primary   = cfg["rated_voltage_primary"],
                    rated_voltage_secondary = cfg["rated_voltage_secondary"],
                    install_year            = cfg["install_year"],
                    lat                     = cfg["lat"],
                    lon                     = cfg["lon"],
                    status                  = "NORMAL",
                ))
                added += 1
        session.commit()
        print(f"[DB] Initialised — {added} transformer(s) seeded.")
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    print("[DB] Schema created successfully.")
