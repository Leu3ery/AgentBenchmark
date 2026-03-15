from backend.statuses import STATUSES
from validation.schema import validate_status


def test_existing_statuses_are_valid():
    assert "draft" in STATUSES
    assert validate_status("active") is True
