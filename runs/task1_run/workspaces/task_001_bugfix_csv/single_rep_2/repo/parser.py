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
            if in_quotes:
                # If next char is also a quote, this is an escaped quote
                if i + 1 < length and line[i + 1] == '"':
                    current.append('"')
                    i += 1  # skip the escaped quote
                else:
                    # closing quote
                    in_quotes = False
            else:
                # opening quote
                in_quotes = True
            i += 1
            continue

        if char == ',' and not in_quotes:
            # end of field
            field = ''.join(current)
            # strip only if the field was not quoted
            parts.append(field.strip())
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    # append last field
    field = ''.join(current)
    parts.append(field.strip())
    return parts
