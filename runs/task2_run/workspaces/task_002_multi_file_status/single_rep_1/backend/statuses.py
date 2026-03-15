STATUSES = [
    "draft",
    "active",
    "disabled",
    "archived",
]

STATUS_LABELS = {
    "draft": "Draft",
    "active": "Active",
    "disabled": "Disabled",
    "archived": "Archived",
}

TERMINAL_STATUSES = {"disabled", "archived"}


def is_valid_status(value: str) -> bool:
    return value in STATUSES


def is_terminal_status(value: str) -> bool:
    return value in TERMINAL_STATUSES
