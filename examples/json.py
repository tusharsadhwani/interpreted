def extract_string(json_string, index, tokens):
    """Extracts a single string token from JSON string"""
    start = index
    end = len(json_string)
    index += 1  # skip over the starting `"`

    while index < end:
        char = json_string[index]

        if char == "\\":
            if index + 1 == end:
                return None

            index += 2  # skip over escaped characters like `\"`
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
            # whitespace is ignored
            index += 1
            continue

        if char in "[]{},:":
            token = {"value": char, "type": "operator"}
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
    if tokens[0]["value"] == "}":
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
        if token["value"] != ":":
            return None

        # Missing value for key
        if len(tokens) == 0:
            return None

        if tokens[0]["value"] == "}":
            return None

        value = _parse(tokens)
        obj[key] = value

        if len(tokens) == 0:
            return None

        token = tokens.popleft()
        if token["value"] not in (",", "}"):
            return None

        if token["value"] == "}":
            break

        # Trailing comma checks
        if len(tokens) == 0:
            return None

        if tokens[0]["value"] == "}":
            return None

    return obj


def parse_array(tokens):
    """Parses an array out of JSON tokens"""
    array = []

    # special case:
    if tokens[0]["value"] == "}":
        tokens.popleft()
        return array

    while tokens:
        value = _parse(tokens)
        array.append(value)

        token = tokens.popleft()
        if token["value"] not in (",", "]"):
            return None

        if token["value"] == "]":
            break

        # trailing comma check
        if len(tokens) == 0:
            return None

        if tokens[0]["value"] == "]":
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

    if token["value"] == "[":
        return parse_array(tokens)

    if token["value"] == "{":
        return parse_object(tokens)

    if token["type"] == "string":
        return parse_string(token)

    if token["type"] == "number":
        return parse_number(token)

    value = token["value"]
    special_tokens = {"true": True, "false": False, "null": None}
    if value in special_tokens:
        return special_tokens[value]


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


print(parse('{"foo": [1, 2, 3, {"bar": [true, false, null]}]}'))

# # larger example
# print(
#     parse(
#         """
#         {
#             "results": [
#                 {
#                 "gender": "male",
#                 "name": { "title": "Mr", "first": "سینا", "last": "موسوی" },
#                 "location": {
#                     "street": { "number": 8134, "name": "میدان امام حسین" },
#                     "city": "ارومیه",
#                     "state": "خوزستان",
#                     "country": "Iran",
#                     "postcode": 24340,
#                     "coordinates": { "latitude": "27.3083", "longitude": "-104.2564" },
#                     "timezone": {
#                     "offset": "0:00",
#                     "description": "Western Europe Time, London, Lisbon, Casablanca"
#                     }
#                 },
#                 "email": "syn.mwswy@example.com",
#                 "login": {
#                     "uuid": "8a6da152-019a-40b4-80b0-bfafd5281fd7",
#                     "username": "sadbear764",
#                     "password": "1947",
#                     "salt": "ddKNbUrc",
#                     "md5": "7ff0c750f9b8d7690d50385754a7fe25",
#                     "sha1": "e140544e222f27a2d0aa809ccb00a1d1ca1fda60",
#                     "sha256": "fd5dbd61da24a82f48971a6d027400a2fd5b0808fd108764f17d87aaa61774d9"
#                 },
#                 "dob": { "date": "1996-12-06T21:55:10.574Z", "age": 24 },
#                 "registered": { "date": "2013-04-07T05:56:17.049Z", "age": 7 },
#                 "phone": "083-15098477",
#                 "cell": "0998-569-1505",
#                 "id": { "name": "", "value": null },
#                 "picture": {
#                     "large": "https://randomuser.me/api/portraits/men/94.jpg",
#                     "medium": "https://randomuser.me/api/portraits/med/men/94.jpg",
#                     "thumbnail": "https://randomuser.me/api/portraits/thumb/men/94.jpg"
#                 },
#                 "nat": "IR"
#                 }
#             ],
#             "info": {
#                 "seed": "db5d8d673b395e5a",
#                 "results": 1,
#                 "page": 1,
#                 "version": "1.3"
#             }
#         }
#         """
#     )
# )
