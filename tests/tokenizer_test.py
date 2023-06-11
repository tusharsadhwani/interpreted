from textwrap import dedent
import pytest

from interpreted.tokenizer import Token, TokenType, Tokenizer


@pytest.mark.parametrize(
    ("source", "tokens"),
    (
        (
            """\
            for i in range(10 % 3):
                i **= 1
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
                Token(token_type=TokenType.NEWLINE, string="\n", start=35, end=35),
                Token(token_type=TokenType.DEDENT, string="", start=36, end=35),
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
    ),
)
def test_tokenizer(source: str, tokens: list[str]):
    assert Tokenizer(dedent(source)).scan_tokens() == tokens
