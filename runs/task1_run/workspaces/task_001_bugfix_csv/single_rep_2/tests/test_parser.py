import sys
from pathlib import Path
# Ensure project root is on sys.path so `import repo` works when pytest changes cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repo.parser import parse_csv_line


def test_basic_csv_line():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_quoted_commas_are_preserved():
    assert parse_csv_line('alpha,"beta,gamma",delta') == ["alpha", "beta,gamma", "delta"]


def test_mixed_quoted_and_plain_fields():
    assert parse_csv_line('one,"two, three",four,"five,six"') == [
        "one",
        "two, three",
        "four",
        "five,six",
    ]
