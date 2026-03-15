def parse_csv_line(line: str) -> list[str]:
    """
    Parse a single CSV line.

    This parser is intentionally small and currently has a bug in how it handles
    quoted fields containing commas.
    """
    parts = []
    current = []
    in_quotes = False
    i = 0
    length = len(line)

    while i < length:
        char = line[i]
        if char == '"':
            # If we're in quotes and the next char is also a quote, this is an escaped quote
            if in_quotes and i + 1 < length and line[i + 1] == '"':
                current.append('"')
                i += 2
                continue
            # Toggle quoted state and skip the quote character
            in_quotes = not in_quotes
            i += 1
            continue
        if char == ',' and not in_quotes:
            parts.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(char)
        i += 1

    parts.append("".join(current).strip())
    return parts
