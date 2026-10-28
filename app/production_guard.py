import os


def validate_production_config():
    environment = os.getenv(
        "GNOME_ENV", "development"
    ).strip().lower()

    enforce_auth = os.getenv(
        "GNOME_ENFORCE_AUTH", "0"
    )

    if (
        environment == "production"
        and enforce_auth != "1"
    ):
        raise RuntimeError(
            "Production requires GNOME_ENFORCE_AUTH=1"
        )

    return True
