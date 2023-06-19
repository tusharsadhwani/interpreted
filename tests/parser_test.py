from textwrap import dedent

import pytest

from interpreted.nodes import (
    Constant,
    ExprStmt,
    Module,
    For,
    Call,
    Name,
    BinOp,
    AugAssign,
)
from interpreted.parser import Parser
from interpreted.tokenizer import Tokenizer


@pytest.mark.parametrize(
    ("source", "tree"),
    (
        (
            """\
            i = 0
            while i < 10:
                i **= 2
                print(i)
            """,
            Module(
                body=[
                    For(
                        target=Name(id="i"),
                        iterable=Call(
                            function=Name(id="range"),
                            args=[
                                BinOp(
                                    left=Constant(value=10),
                                    op="%",
                                    right=Constant(value=3),
                                ),
                            ],
                        ),
                        body=[
                            AugAssign(
                                target=Name(id="i"),
                                op="**",
                                value=Constant(value=2),
                            ),
                            ExprStmt(
                                value=Call(
                                    function=Name("print"),
                                    args=[Name("i")],
                                ),
                            ),
                        ],
                        orelse=[],
                    ),
                ],
            ),
        ),
    ),
)
def test_parser(source: str, tree: Module) -> None:
    tokens = Tokenizer(dedent(source)).scan_tokens()
    assert Parser(tokens).parse() == tree
