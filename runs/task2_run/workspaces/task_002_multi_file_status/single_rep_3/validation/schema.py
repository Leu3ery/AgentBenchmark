ALLOWED_STATUS = {"draft", "active", "disabled", "archived"}


def validate_status(value: str) -> bool:
    return value in ALLOWED_STATUS


def normalize_status(value: str) -> str:
    return value.strip().lower()


def validate_payload(payload: dict) -> bool:
    status = normalize_status(payload["status"])
    return validate_status(status)
