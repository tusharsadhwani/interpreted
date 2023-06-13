from __future__ import annotations

import sys
from enum import Enum, unique
from typing import NamedTuple


@unique
class TokenType(Enum):
    OP = "op"
    NAME = "name"
    STRING = "string"
    NUMBER = "number"
    INDENT = "indent"
    DEDENT = "dedent"
    NEWLINE = "newline"

    def __repr__(self) -> str:
        """This is only there to make the output prettier."""
        return f"{self.__class__.__qualname__}.{self._name_}"


class Token(NamedTuple):
    token_type: TokenType
    string: str
    start: int
    end: int


class TokenizeError(Exception):
    def __init__(self, msg: str, location: int) -> None:
        super().__init__(msg)
        self.location = location


class TokenizeIncompleteError(TokenizeError):
    ...


class Tokenizer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.tokens: list[Token] = []

        self.start = self.next = 0

        self.indent = ""
        self.bracket_level = 0

    @property
    def in_parentheses(self) -> bool:
        return self.bracket_level > 0

    @property
    def scanned(self) -> int:
        """Returns True if the source has been fully scanned."""
        return self.next >= len(self.source)

    def advance(self) -> None:
        self.next += 1

    def skip_token(self) -> str:
        self.start = self.next

    def peek(self) -> str:
        """Returns the current character, without actually consuming it."""
        if self.scanned:
            return ""

        return self.source[self.next]

    def peek_next(self) -> str:
        """Returns the next character, without actually consuming it."""
        if self.next + 1 >= len(self.source):
            return ""

        return self.source[self.next + 1]

    def read_char(self) -> str:
        """
        Reads one character from the source.
        If the source has been exhausted, returns an empty string.
        """
        char = self.source[self.next]
        self.advance()
        return char

    def add_token(self, token_type: TokenType) -> None:
        """Adds a new token for the just-scanned characters."""
        string = self.source[self.start : self.next]
        self.tokens.append(Token(token_type, string, self.start, self.next - 1))
        self.start = self.next

    def scan_tokens(self) -> list[Token]:
        """Scans the source to produce tokens of variables, operators, strings etc."""
        while not self.scanned:
            self.scan_token()

        return self.tokens

    def scan_token(self) -> None:
        char = self.read_char()

        # Indent detection at beginning of line (i.e. after a newline)
        if char == "\n" and not self.in_parentheses:
            self.add_token(TokenType.NEWLINE)
            self.detect_indent()

        # Ignore all whitespace that's not at beginning of line
        elif char in "\f\v\t\r\n ":
            self.skip_token()

        # ** and **= support
        elif char == "*" and self.peek() == "*":
            self.advance()
            if self.peek() == "=":
                self.advance()

            self.add_token(TokenType.OP)

        # comments
        elif char == "/" and self.peek("/"):
            self.advance()
            self.scan_comment()

        # augmented assigns
        elif char in ("+", "-", "*", "/", "=", "!", "@", "%", "^", "&"):
            if self.peek() == "=":
                self.advance()
            self.add_token(TokenType.OP)

        # Notable ommissions: $, #, ', ", `, ? and _
        elif char in ("~", "(", ")", "[", "]", "{", "}", ":", ";", ",", ".", "\\", "|"):
            self.add_token(TokenType.OP)

            # Bracketed statement detection
            if char in ("(", "[", "{"):
                self.bracket_level += 1
            elif char in (")", "]", "}") and self.bracket_level > 0:
                self.bracket_level -= 1

        elif char in ('"', "'"):
            self.scan_string(char)

        elif char.isdigit():
            self.scan_number()

        elif char.isalpha() or char == "_":
            self.scan_identifier()

        else:
            raise TokenizeError(f"Unknown character found: '{char}'", self.start)

    def detect_indent(self) -> None:
        indent = ""
        while not self.scanned and self.peek() in " \t":
            char = self.read_char()
            indent += char

        # the indent must be consistent with the previous one
        if not (indent.startswith(self.indent) or self.indent.startswith(indent)):
            raise TokenizeError("Inconsistent use of tabs and spaces", self.start)

        if len(indent) > len(self.indent):
            self.add_token(TokenType.INDENT)
        elif len(indent) < len(self.indent):
            self.add_token(TokenType.DEDENT)

        self.indent = indent

    def scan_comment(self) -> None:
        """Reads and discards a comment. A comment goes on till a newline."""
        while not self.scanned and self.peek() != "\n":
            self.advance()

        # Since comments are thrown away, reset the start pointer
        self.skip_token()

    def scan_identifier(self) -> None:
        """Scans keywords and variable names."""
        while not self.scanned and (self.peek().isalnum() or self.peek() == "_"):
            self.advance()

        self.add_token(TokenType.NAME)

    def scan_string(self, quote_char: str) -> None:
        while not self.scanned:
            char = self.read_char()

            if char == quote_char:
                self.add_token(TokenType.STRING)
                return

            if char != "\\":
                continue

            # Detecting valid escape sequences
            next_char = self.peek()
            if next_char == "":
                raise TokenizeIncompleteError("Unterminated string", index=self.start)

            if next_char in "\nnrtf'\"\\":
                continue

            # Not implemented: \xHH, \uHHHH and \UHHHHHHHH

            # Raise error for not known escapes
            escape = char + next_char
            raise TokenizeError(
                f"Unknown escape sequence: {escape!r}",
                index=self.next,
            )

        # we never found the end of the string!
        raise TokenizeIncompleteError("Unterminated string", index=self.start)

    def scan_number(self) -> None:
        while self.peek().isdigit():
            self.advance()

        # decimal support
        if self.peek() == "." and self.peek_next().isdigit():
            self.advance()
            while self.peek().isdigit():
                self.advance()

        # exponent part support
        if self.peek() in "eE" and self.peek_next().isdigit():
            self.advance()
            while self.peek().isdigit():
                self.advance()

        self.add_token(TokenType.NUMBER)


if __name__ == "__main__":
    for _token in Tokenizer(sys.stdin.read()).scan_tokens():
        print(_token)
