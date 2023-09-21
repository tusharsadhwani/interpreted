from __future__ import annotations

from textwrap import dedent

import pytest

from interpreted.tokenizer import Token, Tokenizer, TokenType


@pytest.mark.parametrize(
    ("source", "tokens"),
    (
        (
            """\
            for i in range(10 % 3):
                i **= 1  # stuff
            """,
            [
                Token(token_type=TokenType.NAME, string="for", start=0, end=2),
                Token(token_type=TokenType.NAME, string="i", start=4, end=4),
                Token(token_type=TokenType.NAME, string="in", start=6, end=7),
                Token(token_type=TokenType.NAME, string="range", start=9, end=13),
                Token(token_type=TokenType.OP, string="(", start=14, end=14),
                Token(token_type=TokenType.NUMBER, string="10", start=15, end=16),
                Token(token_type=TokenType.OP, string="%", start=18, end=18),
                Token(token_type=TokenType.NUMBER, string="3", start=20, end=20),
                Token(token_type=TokenType.OP, string=")", start=21, end=21),
                Token(token_type=TokenType.OP, string=":", start=22, end=22),
                Token(token_type=TokenType.NEWLINE, string="\n", start=23, end=23),
                Token(token_type=TokenType.INDENT, string="    ", start=24, end=27),
                Token(token_type=TokenType.NAME, string="i", start=28, end=28),
                Token(token_type=TokenType.OP, string="**=", start=30, end=32),
                Token(token_type=TokenType.NUMBER, string="1", start=34, end=34),
                Token(token_type=TokenType.NEWLINE, string="\n", start=44, end=44),
                # TODO: fix end index
                Token(token_type=TokenType.DEDENT, string="", start=45, end=44),
            ],
        ),
        (
            """\
            print(
              'a\\nb'[i]
            )
            2+2
            """,
            [
                Token(token_type=TokenType.NAME, string="print", start=0, end=4),
                Token(token_type=TokenType.OP, string="(", start=5, end=5),
                Token(token_type=TokenType.STRING, string="'a\\nb'", start=9, end=14),
                Token(token_type=TokenType.OP, string="[", start=15, end=15),
                Token(token_type=TokenType.NAME, string="i", start=16, end=16),
                Token(token_type=TokenType.OP, string="]", start=17, end=17),
                Token(token_type=TokenType.OP, string=")", start=19, end=19),
                Token(token_type=TokenType.NEWLINE, string="\n", start=20, end=20),
                Token(token_type=TokenType.NUMBER, string="2", start=21, end=21),
                Token(token_type=TokenType.OP, string="+", start=22, end=22),
                Token(token_type=TokenType.NUMBER, string="2", start=23, end=23),
                Token(token_type=TokenType.NEWLINE, string="\n", start=24, end=24),
            ],
        ),
        (
            """\
            foo
                bar
                    baz
                    baz2
            buzz
                stuff
                      quux
                spam
                  eggs
            bacon
            """,
            [
                Token(token_type=TokenType.NAME, string="foo", start=0, end=2),
                Token(token_type=TokenType.NEWLINE, string="\n", start=3, end=3),
                Token(token_type=TokenType.INDENT, string="    ", start=4, end=7),
                Token(token_type=TokenType.NAME, string="bar", start=8, end=10),
                Token(token_type=TokenType.NEWLINE, string="\n", start=11, end=11),
                Token(token_type=TokenType.INDENT, string="        ", start=12, end=19),
                Token(token_type=TokenType.NAME, string="baz", start=20, end=22),
                Token(token_type=TokenType.NEWLINE, string="\n", start=23, end=23),
                Token(token_type=TokenType.NAME, string="baz2", start=32, end=35),
                Token(token_type=TokenType.NEWLINE, string="\n", start=36, end=36),
                Token(token_type=TokenType.DEDENT, string="", start=37, end=36),
                Token(token_type=TokenType.DEDENT, string="", start=37, end=36),
                Token(token_type=TokenType.NAME, string="buzz", start=37, end=40),
                Token(token_type=TokenType.NEWLINE, string="\n", start=41, end=41),
                Token(token_type=TokenType.INDENT, string="    ", start=42, end=45),
                Token(token_type=TokenType.NAME, string="stuff", start=46, end=50),
                Token(token_type=TokenType.NEWLINE, string="\n", start=51, end=51),
                Token(
                    token_type=TokenType.INDENT, string="          ", start=52, end=61
                ),
                Token(token_type=TokenType.NAME, string="quux", start=62, end=65),
                Token(token_type=TokenType.NEWLINE, string="\n", start=66, end=66),
                Token(token_type=TokenType.DEDENT, string="    ", start=67, end=70),
                Token(token_type=TokenType.NAME, string="spam", start=71, end=74),
                Token(token_type=TokenType.NEWLINE, string="\n", start=75, end=75),
                Token(token_type=TokenType.INDENT, string="      ", start=76, end=81),
                Token(token_type=TokenType.NAME, string="eggs", start=82, end=85),
                Token(token_type=TokenType.NEWLINE, string="\n", start=86, end=86),
                Token(token_type=TokenType.DEDENT, string="", start=87, end=86),
                Token(token_type=TokenType.DEDENT, string="", start=87, end=86),
                Token(token_type=TokenType.NAME, string="bacon", start=87, end=91),
                Token(token_type=TokenType.NEWLINE, string="\n", start=92, end=92),
            ],
        ),
    ),
)
def test_tokenizer(source: str, tokens: list[Token]) -> None:
    assert Tokenizer(dedent(source)).scan_tokens() == tokens
