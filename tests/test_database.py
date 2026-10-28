import sqlite3

from app import database


def test_initialize(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setenv("GNOME_DB_PATH", str(path))

    database.initialize()

    assert path.exists()

    with sqlite3.connect(path) as db:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )
        }

    assert "businesses" in tables
    assert "leads" in tables


def test_business_lead_relationship(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "test.db")
    )

    database.initialize()

    with database.connect() as db:
        db.execute(
            "INSERT INTO businesses(name) VALUES (?)",
            ("Oakridge Supply",)
        )

        db.execute(
            """
            INSERT INTO leads(
                business_id, company, contact
            ) VALUES (?, ?, ?)
            """,
            (1, "Pine Valley", "Alex")
        )

        lead = db.execute(
            "SELECT * FROM leads WHERE business_id = ?",
            (1,)
        ).fetchone()

    assert lead["company"] == "Pine Valley"
    assert lead["status"] == "new"


def test_foreign_key_protection(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "GNOME_DB_PATH",
        str(tmp_path / "test.db")
    )

    database.initialize()

    with database.connect() as db:
        try:
            db.execute(
                """
                INSERT INTO leads(business_id, company)
                VALUES (?, ?)
                """,
                (999, "Invalid Company")
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError(
                "Foreign key protection failed"
            )
