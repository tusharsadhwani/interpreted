from textwrap import dedent

import pytest

from interpreted.nodes import (
    Assign,
    Compare,
    Constant,
    ExprStmt,
    Module,
    Call,
    Name,
    AugAssign,
    While,
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
                    Assign(
                        targets=[Name(id="i")],
                        value=Constant(value=0),
                    ),
                    While(
                        condition=Compare(
                            left=Name(id="i"),
                            op="<",
                            right=Constant(value=10),
                        ),
                        body=[
                            AugAssign(
                                target=Name(id="i"),
                                op="**=",
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


# TODO: extra parens ((((x)))), ((((x, y)))) create tuples
# TODO: multiple return values / receivers are still not properly supported
# TODO: `a == b == c` is not like Python, `10 == 10 in [10, 20]` gives False
