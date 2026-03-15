STATUSES = [
    "draft",
    "active",
    "disabled",
]

STATUS_LABELS = {
    "draft": "Draft",
    "active": "Active",
    "disabled": "Disabled",
}

TERMINAL_STATUSES = {"disabled"}


def is_valid_status(value: str) -> bool:
    return value in STATUSES


def is_terminal_status(value: str) -> bool:
    return value in TERMINAL_STATUSES
