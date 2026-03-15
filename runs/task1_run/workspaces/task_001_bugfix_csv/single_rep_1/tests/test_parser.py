import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

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


def test_escaped_quote_inside_quoted_field():
    # CSV convention: two double-quotes inside a quoted field represent a literal quote
    assert parse_csv_line('a,"b""c",d') == ["a", 'b"c', "d"]
