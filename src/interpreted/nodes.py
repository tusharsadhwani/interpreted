from dataclasses import dataclass
from typing import Literal, TypeAlias

BINOP: TypeAlias = Literal["+", "-", "*", "/", "**", "!", "@", "%", "^", "&"]


@dataclass
class Expression:
    ...


@dataclass
class Constant(Expression):
    value: int | float | bool | str | None


@dataclass
class Name(Expression):
    value: str


@dataclass
class Attribute(Expression):
    value: Expression
    attr: str


@dataclass
class Subscript(Expression):
    value: Expression
    key: Expression


Target: TypeAlias = Name | Attribute | Subscript


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
class Compare(Expression):
    left: Expression
    op: Literal["<", ">", "<=", ">=", "==", "!="]
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
    targets: Expression
    value: Expression


@dataclass
class AugAssign(Statement):
    target: Expression
    op: BINOP
    value: Expression


@dataclass
class Pass(Statement):
    pass


@dataclass
class Return(Statement):
    value: Expression


@dataclass
class Module:
    body: list[Statement]
