from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

BINOP = Literal["+", "-", "*", "/", "**", "@", "%", "^", "&"]
AUGOP = Literal["+=", "-=", "*=", "/=", "**=", "@=", "%=", "^=", "&="]


@dataclass
class Node:
    ...


@dataclass
class Expression(Node):
    ...


@dataclass
class Constant(Expression):
    value: int | float | bool | str | None


@dataclass
class Name(Expression):
    value: str


@dataclass
class List(Expression):
    elements: list[Expression]


@dataclass
class Tuple(Expression):
    elements: list[Expression]


@dataclass
class Dict(Expression):
    keys: list[Expression]
    values: list[Expression]


@dataclass
class Attribute(Expression):
    value: Expression
    attr: str


@dataclass
class Subscript(Expression):
    value: Expression
    key: Expression


@dataclass
class Slice(Expression):
    start: Expression
    end: Expression


Target = Union[Name, Attribute, Subscript]


@dataclass
class Call(Expression):
    function: Expression
    args: list[Expression]


@dataclass
class Name(Expression):
    id: str


@dataclass
class BinOp(Expression):
    left: Expression
    op: BINOP
    right: Expression


@dataclass
class BoolOp(Expression):
    left: Expression
    op: Literal["and", "or"]
    right: Expression


@dataclass
class UnaryOp(Expression):
    value: Expression
    op: Literal["+", "-", "not"]


@dataclass
class Compare(Expression):
    left: Expression
    op: Literal["<", ">", "<=", ">=", "==", "!=", "in", "not in", "is", "is not"]
    right: Expression


@dataclass
class Statement(Node):
    ...


@dataclass
class ExprStmt(Statement):
    value: Expression


@dataclass
class FunctionDef(Statement):
    name: str
    params: list[str]
    body: list[Statement]
    decorators: list[Decorator] = field(default_factory=list)


@dataclass
class For(Statement):
    target: Expression
    iterable: Expression
    body: list[Statement]
    orelse: list[Statement]


@dataclass
class If(Statement):
    condition: Expression
    body: list[Statement]
    orelse: list[Statement]


@dataclass
class While(Statement):
    condition: Expression
    body: list[Statement]
    orelse: list[Statement]


@dataclass
class Assign(Statement):
    targets: list[Expression]
    value: Expression


@dataclass
class AugAssign(Statement):
    target: Expression
    op: AUGOP
    value: Expression


@dataclass
class Pass(Statement):
    pass


@dataclass
class Break(Statement):
    pass


@dataclass
class Continue(Statement):
    pass


@dataclass
class Return(Statement):
    value: Expression


@dataclass
class alias:
    name: str
    asname: str | None


@dataclass
class Import(Statement):
    names: list[alias]


@dataclass
class ImportFrom(Statement):
    module: str
    names: list[alias]


@dataclass
class Module:
    body: list[Statement]


@dataclass
class Decorator(Node):
    value: Expression
