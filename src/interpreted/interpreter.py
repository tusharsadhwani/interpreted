from __future__ import annotations
from collections import deque

from typing import Any
from unittest import mock

from interpreted import nodes
from interpreted.nodes import (
    Assign,
    Attribute,
    AugAssign,
    Call,
    Compare,
    Constant,
    Dict,
    ExprStmt,
    FunctionDef,
    If,
    Module,
    Name,
    Node,
    Subscript,
    While,
)
from interpreted.parser import parse

NOT_SET = object()


class Scope:
    def get(self, name) -> Any:
        return getattr(self, name, NOT_SET)

    def set(self, name, value) -> None:
        setattr(self, name, value)


class InterpreterError(Exception):
    ...


class Object:
    """Every object will inherit this in this implementation."""

    def __init__(self) -> None:
        self.attributes = {}
        self.methods = {}

    def as_string(self) -> None:
        raise NotImplementedError


class Function(Object):
    def as_string(self) -> str:
        raise NotImplementedError

    def arg_count(self) -> int:
        raise NotImplementedError

    def ensure_args(self, args: list[Object]) -> Object:
        if len(args) != self.arg_count():
            raise InterpreterError(
                f"{self.as_string()} takes {self.arg_count()} arguments, {len(args)} given",
            )

    def call(self, interpreter: Interpreter, args: list[Object]) -> None:
        raise NotImplementedError


class Print(Function):
    def as_string(self) -> str:
        return "<function 'print'>"

    def arg_count(self) -> int:
        return mock.ANY

    def call(self, _: Interpreter, args: list[Object]) -> None:
        print(*[arg.as_string() for arg in args])


class Len(Function):
    def as_string(self) -> str:
        return "<function 'len'>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> Object:
        super().ensure_args(args)

        item = args[0]
        if isinstance(item, (List, Deque)):
            return Value(len(item._data))

        if isinstance(item, Value) and isinstance(item.value, str):
            return Value(len(item.value))

        raise InterpreterError(f"{type(item).__name__} has no len()")


class Break(Exception):
    """This is thrown when a loop breaks."""


class Continue(Exception):
    """This is thrown when a loop continues."""


class Return(Exception):
    """This is thrown when something returns a value."""

    def __init__(self, value: Object) -> None:
        self.value = value


class UserFunction(Function):
    def __init__(self, definition: FunctionDef) -> None:
        self.definition = definition

    def as_string(self) -> str:
        return f"<function {self.definition.name!r}>"

    def arg_count(self) -> int:
        return len(self.definition.params)

    def call(self, interpreter: Interpreter, args: list[Object]) -> Object:
        super().ensure_args(args)

        parent_scope = interpreter.scope

        function_scope = Scope()
        interpreter.scope = function_scope

        for param, arg in zip(self.definition.params, args):
            function_scope.set(param, arg)

        try:
            for statement in self.definition.body:
                interpreter.visit(statement)

        except Return as ret:
            return ret.value

        finally:
            interpreter.scope = parent_scope

        return None


class DequeConstructor(Function):
    def as_string(self) -> str:
        return "<function 'deque'>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> None:
        super().ensure_args(args)
        return Deque()


class Deque(Object):
    def as_string(self) -> str:
        return f"<deque [" + ", ".join(item.as_string() for item in self._data) + "]>"

    def __init__(self) -> None:
        super().__init__()

        self._data = deque()

        self.methods["append"] = Append(self)
        self.methods["popleft"] = PopLeft(self)


class Append(Function):
    def __init__(self, wrapper: List | Deque) -> None:
        super().__init__()
        self.wrapper = wrapper

    def as_string(self) -> str:
        return f"<method 'append' of {self.wrapper.as_string()}>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> None:
        super().ensure_args(args)
        item = args[0]
        self.wrapper._data.append(item)


class PopLeft(Function):
    def __init__(self, deque: Deque) -> None:
        super().__init__()
        self.deque = deque

    def as_string(self) -> str:
        return f"<method 'popleft' of {self.deque.as_string()}>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> None:
        super().ensure_args(args)
        return self.deque._data.popleft()


class Value(Object):
    def __init__(self, value: Any) -> None:
        self.value = value

    def as_string(self) -> None:
        return str(self.value)


class List(Object):
    def as_string(self) -> str:
        return f"[" + ", ".join(item.as_string() for item in self._data) + "]"

    def __init__(self, elements=None) -> None:
        super().__init__()

        if elements is None:
            elements = []

        self._data = elements

        self.methods["append"] = Append(self)


def is_truthy(obj: Object) -> bool:
    if isinstance(obj, Value):
        return bool(obj.value)

    return True


class Interpreter:
    def __init__(self) -> None:
        self.globals = Scope()
        self.globals.set("print", Print())
        self.globals.set("len", Len())
        self.globals.set("deque", DequeConstructor())

        self.scope = self.globals

    def visit(self, node: Node) -> Object | None:
        node_type = type(node).__name__
        visitor_method = getattr(self, f"visit_{node_type}")
        return visitor_method(node)

    def visit_Module(self, node: Module) -> None:
        for stmt in node.body:
            self.visit(stmt)

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        function = UserFunction(node)
        self.scope.set(node.name, function)

    def visit_Assign(self, node: Assign) -> None:
        value = self.visit(node.value)
        assert len(node.targets) == 1  # TODO
        target = node.targets[0]

        if isinstance(target, Name):
            self.scope.set(target.id, value)
        else:
            raise NotImplementedError(target)  # TODO

    def visit_AugAssign(self, node: AugAssign) -> None:
        increment = self.visit(node.value)
        assert isinstance(increment, Value)  # TODO: list +=

        target = node.target
        if isinstance(target, Name):
            current_value = self.visit(target)
            assert isinstance(current_value, Value)  # TODO: list +=
            if node.op == "+=":
                new_value = Value(current_value.value + increment.value)
            else:
                raise NotImplementedError(node)

            self.scope.set(target.id, new_value)
        else:
            raise NotImplementedError(target)  # TODO

    def visit_If(self, node: If) -> None:
        if is_truthy(self.visit(node.condition)):
            for stmt in node.body:
                self.visit(stmt)
        else:
            for stmt in node.orelse:
                self.visit(stmt)

    def visit_While(self, node: While) -> None:
        while is_truthy(self.visit(node.condition)):
            for stmt in node.body:
                try:
                    self.visit(stmt)
                except Break:
                    return
                except Continue:
                    continue

        # TODO: else on while

    def visit_Break(self, node: nodes.Break) -> Break:
        raise Break

    def visit_Continue(self, node: nodes.Continue) -> Continue:
        raise Continue

    def visit_Return(self, node: nodes.Return) -> Return:
        raise Return(self.visit(node.value))

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        self.visit(node.value)

    def visit_Compare(self, node: Compare) -> Value:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if not isinstance(left, Value) or not isinstance(right, Value):
            raise InterpreterError(
                f"Cannot compare a {type(left).__name__}"
                f" and a {type(right).__name__}"
            )

        if node.op == "==":
            return Value(left.value == right.value)
        if node.op == "!=":
            return Value(left.value != right.value)
        if node.op == "<":
            return Value(left.value < right.value)
        if node.op == ">":
            return Value(left.value > right.value)
        if node.op == "in":
            return Value(left.value in right.value)

        raise NotImplementedError(node)

    def visit_BinOp(self, node) -> Object:
        left = self.visit(node.left)
        right = self.visit(node.right)

        if not isinstance(left, Value) or not isinstance(right, Value):
            raise InterpreterError(
                f"Cannot compare a {type(left).__name__}"
                f" and a {type(right).__name__}"
            )

        if node.op == "+":
            return Value(left.value + right.value)
        if node.op == "-":
            return Value(left.value - right.value)
        if node.op == "*":
            return Value(left.value * right.value)
        if node.op == "//":
            return Value(left.value / right.value)

        raise NotImplementedError(node)

    def visit_Call(self, node: Call) -> Object:
        function = self.visit(node.function)
        if not isinstance(function, Function):
            object_type = function.__class__.__name__
            raise InterpreterError(f"{object_type!r} object is not callable")

        arguments = [self.visit(arg) for arg in node.args]
        return function.call(self, arguments)

    def visit_Subscript(self, node: Subscript) -> Object:
        obj = self.visit(node.value)
        assert obj is not None

        key = self.visit(node.key)

        if isinstance(obj, (List, Dict)) and key in obj._data:
            return obj._data[key]
        if (
            isinstance(obj, Value)
            and isinstance(obj.value, str)
            and isinstance(key, Value)
        ):
            return Value(obj.value[key.value])

        raise InterpreterError(f"{type(obj).__name__} object has no key {key!r}")

    def visit_Attribute(self, node: Attribute) -> Object:
        attribute_name = node.attr
        obj = self.visit(node.value)
        assert obj is not None

        if attribute_name in obj.attributes:
            return obj.attributes[attribute_name]

        elif attribute_name in obj.methods:
            return obj.methods[attribute_name]

        raise InterpreterError(
            f"{type(obj).__name__} object has no attribute {attribute_name!r}"
        )

    def visit_Name(self, node: Name) -> Value:
        name = node.id

        value = self.scope.get(name)
        if value is NOT_SET:
            value = self.globals.get(name)
            if value is NOT_SET:
                raise InterpreterError(f"{name!r} is not defined")

        return value

    def visit_List(self, node: nodes.List) -> List:
        elements = [self.visit(element) for element in node.elements]
        return List(elements)

    def visit_Dict(self, node: nodes.Dict) -> Dict:
        keys = [self.visit(key) for key in node.keys]
        values = [self.visit(key) for key in node.keys]
        return Dict(keys, values)

    def visit_Constant(self, node: Constant) -> Value:
        return Value(node.value)


def interpret(source: str) -> None:
    module = parse(source)
    if module is None:
        return

    Interpreter().visit(module)
