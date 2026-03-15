from backend.statuses import STATUS_LABELS


def serialize_record(record: dict) -> dict:
    status = record["status"]
    return {
        "id": record["id"],
        "status": status,
        "status_label": STATUS_LABELS[status],
    }
