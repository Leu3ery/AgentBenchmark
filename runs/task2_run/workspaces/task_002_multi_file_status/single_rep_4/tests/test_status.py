from api.serializer import serialize_record
from backend.statuses import STATUSES, STATUS_LABELS, is_terminal_status
from validation.schema import normalize_status, validate_payload, validate_status


def test_existing_statuses_are_valid():
    assert "draft" in STATUSES
    assert validate_status("active") is True


def test_archived_is_added_to_status_catalog():
    assert "archived" in STATUSES
    assert STATUS_LABELS["archived"] == "Archived"


def test_archived_is_terminal_and_validates():
    assert is_terminal_status("archived") is True
    assert validate_status("archived") is True
    assert normalize_status(" Archived ") == "archived"
    assert validate_payload({"status": "archived"}) is True


def test_serializer_supports_archived():
    payload = serialize_record({"id": "rec_1", "status": "archived"})
    assert payload == {
        "id": "rec_1",
        "status": "archived",
        "status_label": "Archived",
    }
