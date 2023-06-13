from dataclasses import dataclass
from typing import Literal, TypeAlias

OP: TypeAlias = Literal["+", "-", "*", "/", "**", "!", "@", "%", "^", "&"]


@dataclass
class Expression:
    ...


@dataclass
class Constant(Expression):
    value: int | float | bool | str | None


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
    op: OP
    right: Expression


@dataclass
class Statement:
    ...


@dataclass
class ExprStmt(Statement):
    value: Expression


@dataclass
class For(Statement):
    target: Expression
    iterable: Expression
    body: list[Statement]
    orelse: list[Statement]


@dataclass
class Assign(Statement):
    target: Expression
    value: Expression


@dataclass
class AugAssign(Statement):
    target: Expression
    op: OP
    value: Expression


@dataclass
class Module:
    body: list[Statement]
