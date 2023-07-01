def extract_string(json_string, index, tokens):
    """Extracts a single string token from JSON string"""
    start = index
    end = len(json_string)
    index += 1

    while index < end:
        char = json_string[index]

        if char == "\\":
            if index + 1 == end:
                return None

            index += 2
            continue

        if char == '"':
            index += 1
            string = json_string[start:index]
            tokens.append({"value": string, "type": "string"})

            return index

        index += 1

    return None


def extract_number(json_string, index, tokens):
    """Extracts a single number token (eg. 42, -12.3) from JSON string"""
    start = index
    end = len(json_string)

    leading_minus_found = False
    decimal_point_found = False

    while index < end:
        char = json_string[index]
        if char == ".":
            if decimal_point_found:
                return None

            decimal_point_found = True

        elif char == "-":
            if leading_minus_found:
                return None

            leading_minus_found = True

        elif not char.isdigit():
            break

        index += 1

    number = json_string[start:index]
    tokens.append({"value": number, "type": "number"})
    return index


def extract_special(json_string, index, tokens):
    """Extracts true, false and null from JSON string"""
    end = len(json_string)

    word = ""
    while index < end:
        char = json_string[index]
        if not char.isalpha():
            break

        word += char
        index += 1

    if word == "true":
        token = {"value": word, "type": "boolean"}
    elif word == "false":
        token = {"value": word, "type": "boolean"}
    elif word == "null":
        token = {"value": word, "type": "null"}
    else:
        return None

    tokens.append(token)
    return index


def tokenize(json_string):
    """Converts a JSON string into a queue of tokens"""
    tokens = deque()

    index = 0
    end = len(json_string)
    while index < end:
        char = json_string[index]

        if char in " \n\t":
            index += 1
            continue

        if char in "[]{},:":
            if char == "[":
                type = "left_bracket"
            elif char == "]":
                type = "right_bracket"
            elif char == "{":
                type = "left_brace"
            elif char == "}":
                type = "right_brace"
            elif char == ",":
                type = "comma"
            else:
                type = "colon"

            token = {"value": char, "type": type}
            tokens.append(token)
            index += 1
            continue

        if char == '"':
            new_index = extract_string(json_string, index, tokens)

        elif char == "-" or char.isdigit():
            new_index = extract_number(json_string, index, tokens)

        else:
            new_index = extract_special(json_string, index, tokens)

        if new_index is None:
            print("Parsing error at index", index)
            return None
        else:
            index = new_index

    return tokens


def parse_object(tokens):
    """Parses an object out of JSON tokens"""
    obj = {}

    # special case:
    if tokens[0]["type"] == "right_brace":
        tokens.popleft()
        return obj

    while tokens:
        token = tokens.popleft()

        if not token["type"] == "string":
            return None

        key = parse_string(token)

        if len(tokens) == 0:
            return None

        token = tokens.popleft()
        if token["type"] != "colon":
            return None

        # Missing value for key
        if len(tokens) == 0:
            return None

        if tokens[0]["type"] == "right_brace":
            token = tokens[0]
            return None

        value = _parse(tokens)
        obj[key] = value

        if len(tokens) == 0:
            return None

        token = tokens.popleft()
        if token["type"] not in ("comma", "right_brace"):
            return None

        if token["type"] == "right_brace":
            break

        # Trailing comma checks
        if len(tokens) == 0:
            return None

        if tokens[0]["type"] == "right_brace":
            return None

    return obj


def parse_array(tokens):
    """Parses an array out of JSON tokens"""
    array = []

    # special case:
    if tokens[0]["type"] == "right_bracket":
        tokens.popleft()
        return array

    while tokens:
        value = _parse(tokens)
        array.append(value)

        token = tokens.popleft()
        if token["type"] not in ("comma", "right_bracket"):
            return None

        if token["type"] == "right_bracket":
            break

        # trailing comma check
        if len(tokens) == 0:
            return None

        if tokens[0]["type"] == "right_bracket":
            return None

    return array


def parse_string(token):
    """Parses a string out of a JSON token"""
    chars = []

    index = 1
    end = len(token["value"]) - 1

    while index < end:
        char = token["value"][index]

        if char != "\\":
            chars.append(char)
            index += 1
            continue

        next_char = token["value"][index + 1]

        if next_char in ('"', "/", "\\"):
            chars.append(next_char)
        elif next_char == "f":
            chars.append("\f")
        elif next_char == "n":
            chars.append("\n")
        elif next_char == "r":
            chars.append("\r")
        elif next_char == "t":
            chars.append("\t")
        else:
            return None

        index += 2

    string = "".join(chars)
    return string


def parse_number(token):
    """Parses a number out of a JSON token"""
    if token["value"].isdigit():
        number = int(token["value"])
    else:
        number = float(token["value"])

    return number


def _parse(tokens):
    """Recursive JSON parse implementation"""
    token = tokens.popleft()

    if token["type"] == "left_bracket":
        return parse_array(tokens)

    if token["type"] == "left_brace":
        return parse_object(tokens)

    if token["type"] == "string":
        return parse_string(token)

    if token["type"] == "number":
        return parse_number(token)

    special_tokens = {"true": True, "false": False, "null": None}
    if token["type"] in ("boolean", "null"):
        return special_tokens[token["value"]]


def parse(json_string):
    """Parses a JSON string into a Python object"""
    tokens = tokenize(json_string)
    if tokens is None:
        print("Skipping parsing.")
        return None

    value = _parse(tokens)
    if value is None:
        print("Failed to parse, at token", tokens[0])

    return value


print(parse('{"foo": 1}'))
print(parse('{"foo": [1, 2, 3, null]}'))
