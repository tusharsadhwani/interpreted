from __future__ import annotations

from typing import Any
from unittest import mock

from interpreted.nodes import (
    Assign,
    Call,
    Constant,
    ExprStmt,
    FunctionDef,
    Module,
    Name,
    Node,
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


class Function(Object):
    def arg_count(self) -> int:
        raise NotImplementedError

    def call(self, interpreter: Interpreter, args: list[Object]) -> Object:
        raise NotImplementedError


class Return(Exception):
    """This is thrown when something returns a value."""

    def __init__(self, value: Object) -> None:
        self.value = value


class UserFunction(Function):
    def __init__(self, definition: FunctionDef) -> None:
        self.definition = definition

    def arg_count(self) -> int:
        return len(self.definition.params)

    def call(self, interpreter: Interpreter, args: list[Object]) -> Object:
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


class Print(Function):
    def as_string(self) -> None:
        return self.value

    def arg_count(self) -> int:
        return mock.ANY

    def call(self, _: Interpreter, args: list[Object]) -> None:
        print(*[arg.as_string() for arg in args])


class Value(Object):
    def __init__(self, value: Any) -> None:
        self.value = value

    def as_string(self) -> None:
        return self.value


class Interpreter:
    def __init__(self) -> None:
        self.globals = Scope()
        self.globals.set("print", Print())

        self.scope = self.globals

    def visit(self, node: Node) -> Node | None:
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

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        self.visit(node.value)

    def visit_Call(self, node: Call) -> Object:
        function = self.visit(node.function)
        if not isinstance(function, Function):
            object_type = function.__class__.__name__
            raise InterpreterError(f"{object_type!r} object is not callable")

        arguments = [self.visit(arg) for arg in node.args]
        return function.call(self, arguments)

    def visit_Name(self, node: Name) -> None:
        name = node.id

        value = self.scope.get(name)
        if value is NOT_SET:
            value = self.globals.get(name)
            if value is NOT_SET:
                raise InterpreterError(f"{name!r} is not defined")

        return value

    def visit_Constant(self, node: Constant) -> Value:
        return Value(node.value)


def interpret(source: str) -> None:
    module = parse(source)
    if module is None:
        return

    Interpreter().visit(module)
