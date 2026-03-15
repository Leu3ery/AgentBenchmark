def parse_csv_line(line: str) -> list[str]:
    """
    Parse a single CSV line.

    This parser is intentionally small and currently has a bug in how it handles
    quoted fields containing commas.
    """
    parts = []
    current = []
    in_quotes = False

    for char in line:
        if char == '"':
            in_quotes = not in_quotes
            continue
        if char == ",":
            if not in_quotes:
                parts.append("".join(current).strip())
                current = []
                continue
            else:
                # comma inside quoted field → keep it
                current.append(char)
                continue
        current.append(char)

    parts.append("".join(current).strip())
    return parts
