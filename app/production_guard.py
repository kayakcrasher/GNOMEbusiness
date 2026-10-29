import os


def validate_production_config():
    environment = os.getenv(
        "GNOME_ENV", "production"
    ).strip().lower()

    if environment not in {
        "production",
        "development",
        "test",
    }:
        raise RuntimeError(
            "Invalid GNOME_ENV value"
        )

    enforce_auth = os.getenv(
        "GNOME_ENFORCE_AUTH", "1"
    )

    if enforce_auth not in {"0", "1"}:
        raise RuntimeError(
            "Invalid GNOME_ENFORCE_AUTH value"
        )

    if (
        environment == "production"
        and enforce_auth != "1"
    ):
        raise RuntimeError(
            "Production requires authentication"
        )

    return True
