ALLOWED_STATUS = {"draft", "active", "disabled"}


def validate_status(value: str) -> bool:
    return value in ALLOWED_STATUS
