from textwrap import dedent

import pytest

from interpreted.nodes import (
    Assign,
    AugAssign,
    Call,
    Compare,
    Constant,
    ExprStmt,
    Import,
    ImportFrom,
    Module,
    Name,
    While,
    alias,
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
        (
            """\
            import ast, mod
            import module_name
            import module_name as alias, othername as other_alias
            import package_name.module_name
            import a.b.c
            """,
            Module(
                body=[
                    Import(
                        names=[
                            alias(name="ast", asname=None),
                            alias(name="mod", asname=None),
                        ]
                    ),
                    Import(names=[alias(name="module_name", asname=None)]),
                    Import(
                        names=[
                            alias(name="module_name", asname="alias"),
                            alias(name="othername", asname="other_alias"),
                        ]
                    ),
                    Import(names=[alias(name="package_name.module_name", asname=None)]),
                    Import(names=[alias(name="a.b.c", asname=None)]),
                ]
            ),
        ),
        (
            """\
            from module_name import *
            from module_name import name1, name2
            from module_name import name1 as alias1, name2 as alias2
            from package_name.submodule import submodule_name
            from mod.submod.meh import ara as a, b as aux
            """,
            Module(
                body=[
                    ImportFrom(
                        module="module_name", names=[alias(name="*", asname=None)]
                    ),
                    ImportFrom(
                        module="module_name",
                        names=[
                            alias(name="name1", asname=None),
                            alias(name="name2", asname=None),
                        ],
                    ),
                    ImportFrom(
                        module="module_name",
                        names=[
                            alias(name="name1", asname="alias1"),
                            alias(name="name2", asname="alias2"),
                        ],
                    ),
                    ImportFrom(
                        module="package_name.submodule",
                        names=[alias(name="submodule_name", asname=None)],
                    ),
                    ImportFrom(
                        module="mod.submod.meh",
                        names=[
                            alias(name="ara", asname="a"),
                            alias(name="b", asname="aux"),
                        ],
                    ),
                ]
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
