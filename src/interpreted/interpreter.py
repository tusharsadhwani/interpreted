from __future__ import annotations

from collections import deque
from typing import Any
from unittest import mock
import sys

from interpreted import nodes
from interpreted.nodes import (
    Assign,
    Attribute,
    AugAssign,
    BinOp,
    BoolOp,
    Call,
    Compare,
    Constant,
    ExprStmt,
    FunctionDef,
    If,
    Import,
    ImportFrom,
    Module,
    Name,
    Node,
    Slice,
    Subscript,
    UnaryOp,
    While,
    alias,
)
from interpreted.parser import parse

NOT_SET = object()


class Scope:
    def __init__(self, parent=None) -> None:
        self.data = {}
        self.parent = parent
        self.set("print", Print())
        self.set("len", Len())
        self.set("int", Int())
        self.set("float", Float())
        self.set("deque", DequeConstructor())
        self.set("enumerate", Enumerate())

    def get(self, name) -> Any:
        return self.data.get(name, NOT_SET)

    def set(self, name, value) -> None:
        self.data[name] = value


class InterpreterError(Exception):
    ...


class Object:
    """Every object will inherit this in this implementation."""

    def __init__(self) -> None:
        self.attributes = {}
        self.methods = {}

    def as_string(self) -> str:
        raise NotImplementedError

    def repr(self) -> str:
        return self.as_string()


class Module(Object):
    def __init__(self, members: dict[str, Object]):
        super().__init__()
        self.attributes.update(members)


class Function(Object):
    def as_string(self) -> str:
        raise NotImplementedError

    def arg_count(self) -> int:
        raise NotImplementedError

    def ensure_args(self, args: list[Object]) -> Object:
        if len(args) != self.arg_count():
            raise InterpreterError(
                f"{self.repr()} takes {self.arg_count()} arguments, {len(args)} given",
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
        if isinstance(item, (List, Tuple, Deque)):
            return Value(len(item._data))

        if isinstance(item, Value) and isinstance(item.value, str):
            return Value(len(item.value))

        raise InterpreterError(f"{type(item).__name__} has no len()")


class Enumerate(Function):
    def as_string(self) -> str:
        return "<function 'enumerate'>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> Object:
        super().ensure_args(args)
        for idx, val in enumerate(args[0]):
            yield Tuple([Value(idx), val])


class Int(Function):
    def as_string(self) -> str:
        return "<function 'int'>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> Object:
        super().ensure_args(args)

        item = args[0]
        if isinstance(item, Value) and isinstance(item.value, (int, str, float)):
            return Value(int(item.value))

        raise InterpreterError(f"Invalid type for int(): {type(item).__name__}")


class Float(Function):
    def as_string(self) -> str:
        return "<function 'float'>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> Object:
        super().ensure_args(args)

        item = args[0]
        if isinstance(item, Value) and isinstance(item.value, (int, str, float)):
            return Value(float(item.value))

        raise InterpreterError(f"Invalid type for float(): {type(item).__name__}")


class Break(Exception):
    """This is thrown when a loop breaks."""


class Continue(Exception):
    """This is thrown when a loop continues."""


class Return(Exception):
    """This is thrown when something returns a value."""

    def __init__(self, value: Object) -> None:
        self.value = value


class UserFunction(Function):
    def __init__(
        self,
        definition: FunctionDef,
        parent_scope: Scope,
        current_globals: Scope,
    ) -> None:
        self.definition = definition
        self.parent_scope = parent_scope
        self.current_globals = current_globals

    def as_string(self) -> str:
        return f"<function {self.definition.name!r}>"

    def arg_count(self) -> int:
        return len(self.definition.params)

    def call(self, interpreter: Interpreter, args: list[Object]) -> Object:
        super().ensure_args(args)

        current_scope = interpreter.scope
        parent_globals = interpreter.globals

        function_scope = Scope(parent=self.parent_scope)
        interpreter.globals = self.current_globals
        interpreter.scope = function_scope

        for param, arg in zip(self.definition.params, args):
            function_scope.set(param, arg)

        try:
            for statement in self.definition.body:
                interpreter.visit(statement)

        except Return as ret:
            return ret.value

        finally:
            interpreter.scope = current_scope
            interpreter.globals = parent_globals

        return Value(None)


class DequeConstructor(Function):
    def as_string(self) -> str:
        return "<function 'deque'>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> None:
        super().ensure_args(args)
        return Deque()


class Deque(Object):
    def __init__(self) -> None:
        super().__init__()

        self._data = deque()

        self.methods["append"] = Append(self)
        self.methods["popleft"] = PopLeft(self)

    def as_string(self) -> str:
        return f"<deque [" + ", ".join(item.repr() for item in self._data) + "]>"


class Append(Function):
    def __init__(self, wrapper: List | Deque) -> None:
        super().__init__()
        self.wrapper = wrapper

    def as_string(self) -> str:
        return f"<method 'append' of {self.wrapper.repr()}>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> None:
        super().ensure_args(args)
        item = args[0]
        self.wrapper._data.append(item)


class Items(Function):
    def __init__(self, wrapper: Dict) -> None:
        super().__init__()
        self.wrapper = wrapper

    def as_string(self) -> str:
        return f"<method 'items' of {self.wrapper.repr()}>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> Any:
        super().ensure_args(args)
        for kvp in self.wrapper._dict.items():
            yield Tuple(kvp)


class PopLeft(Function):
    def __init__(self, deque: Deque) -> None:
        super().__init__()
        self.deque = deque

    def as_string(self) -> str:
        return f"<method 'popleft' of {self.deque.repr()}>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> None:
        super().ensure_args(args)
        return self.deque._data.popleft()


class Value(Object):
    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value
        if isinstance(value, str):
            self.methods["isdigit"] = IsDigit(self)
            self.methods["isalpha"] = IsAlpha(self)
            self.methods["join"] = Join(self)

    def __eq__(self, other: Object) -> int:
        if not isinstance(other, Value):
            return False

        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"Value({self.value!r})"

    def as_string(self) -> None:
        return str(self.value)

    def repr(self) -> None:
        return repr(self.value)


class IsDigit(Function):
    def __init__(self, wrapper: Value) -> None:
        super().__init__()
        self.wrapper = wrapper

    def as_string(self) -> str:
        return f"<method 'isdigit' of {self.wrapper.repr()}>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> Value:
        super().ensure_args(args)
        return Value(self.wrapper.value.isdigit())


class IsAlpha(Function):
    def __init__(self, wrapper: Value) -> None:
        super().__init__()
        self.wrapper = wrapper

    def as_string(self) -> str:
        return f"<method 'isalpha' of {self.wrapper.repr()}>"

    def arg_count(self) -> int:
        return 0

    def call(self, _: Interpreter, args: list[Object]) -> Value:
        super().ensure_args(args)
        return Value(self.wrapper.value.isalpha())


class Join(Function):
    def __init__(self, wrapper: Value) -> None:
        super().__init__()
        self.wrapper = wrapper

    def as_string(self) -> str:
        return f"<method 'join' of {self.wrapper.repr()}>"

    def arg_count(self) -> int:
        return 1

    def call(self, _: Interpreter, args: list[Object]) -> Value:
        super().ensure_args(args)
        items = args[0]
        if not isinstance(items, (List, Tuple, Deque)):
            raise InterpreterError(f"{type(items).__name__} object is not iterable")

        return Value(self.wrapper.value.join(item.as_string() for item in items._data))


class List(Object):
    def __init__(self, elements) -> None:
        super().__init__()
        self._data = elements
        self.methods["append"] = Append(self)

    def as_string(self) -> str:
        return "[" + ", ".join(item.repr() for item in self._data) + "]"

    # TODO Review this
    def __iter__(self):
        return self._data.__iter__()

class Tuple(Object):
    def __init__(self, elements) -> None:
        super().__init__()
        self._data = elements

    def as_string(self) -> str:
        return "(" + ", ".join(item.repr() for item in self._data) + ")"


class Dict(Object):
    def __init__(self, keys: list[Object], values: list[Object]) -> None:
        super().__init__()
        self._dict = {key: value for key, value in zip(keys, values, strict=True)}
        self.methods["items"] = Items(self)

    def as_string(self) -> str:
        return (
            "{"
            + ", ".join(
                f"{key.repr()}: {value.repr()}" for key, value in self._dict.items()
            )
            + "}"
        )

    # TODO review this
    def __iter__(self):
        return self._dict.__iter__()

def is_truthy(obj: Object) -> bool:
    if isinstance(obj, Value):
        return bool(obj.value)

    return True


class Interpreter:
    def __init__(self) -> None:
        self.globals = Scope()
        self.scope = self.globals

    def visit(self, node: Node) -> Object | None:
        node_type = type(node).__name__
        visitor_method = getattr(self, f"visit_{node_type}")
        return visitor_method(node)

    def visit_Module(self, node: Module) -> None:
        for stmt in node.body:
            self.visit(stmt)

    def visit_Import(self, node: Import) -> None:
        for alias in node.names:
            name = alias.name
            if alias.asname:
                name = alias.asname

            contents = ""
            with open(f"{alias.name}.py", "r") as f:
                contents = f.read()
            module = parse(contents)

            parent_scope = self.scope
            parent_globals = self.globals

            module_scope = Scope()
            self.scope = module_scope
            self.globals = module_scope

            self.visit(module)

            self.scope = parent_scope
            self.globals = parent_globals

            module_obj = Module(members=module_scope.data)

            self.scope.set(name, module_obj)

    def visit_ImportFrom(self, node: ImportFrom) -> None:
        module_name = node.module

        contents = ""
        with open(f"{module_name}.py", "r") as f:
            contents = f.read()
        module = parse(contents)

        parent_scope = self.scope
        parent_globals = self.globals

        module_scope = Scope()
        self.scope = module_scope
        self.globals = module_scope

        self.visit(module)

        self.scope = parent_scope
        self.globals = parent_globals

        for alias in node.names:
            name = alias.name
            if name == "*":
                for member, value in module_scope.data.items():
                    self.scope.set(member, value)
                return

            if alias.asname:
                name = alias.asname

            member = module_scope.get(alias.name)
            self.scope.set(name, member)

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        parent_scope = self.scope
        function = UserFunction(node, parent_scope, self.globals)

        decorators = reversed(node.decorators)

        for decorator_node in decorators:
            decorator = self.visit(decorator_node.value)

            if not isinstance(decorator, Function):
                object_type = decorator.__class__.__name__
                raise InterpreterError(f"{object_type!r} object is not callable")

            function = decorator.call(self, [function])

        self.scope.set(node.name, function)

    def visit_Assign(self, node: Assign) -> None:
        value = self.visit(node.value)
        assert len(node.targets) == 1  # TODO
        target = node.targets[0]

        if isinstance(target, Name):
            self.scope.set(target.id, value)

        elif isinstance(target, Subscript):
            obj = self.visit(target.value)

            if isinstance(obj, (List, Deque)):
                key = self.visit(target.key)
                if not (isinstance(key, Value) and isinstance(key.value, int)):
                    raise InterpreterError(
                        f"Expected integer index for {type(obj).__name__},"
                        f" got {key.repr()}"
                    )

                obj._data[key.value] = value

            elif isinstance(obj, Dict):
                key = self.visit(target.key)
                obj._dict[key] = value

            else:
                raise InterpreterError(
                    f"Index not implemented for {type(obj).__name__}"
                )

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

    def visit_For(self, node: For) -> None:
        if len(node.iterable) == 1:
            elements = self.visit(node.iterable[0])
        else:
            elements = [self.visit(e) for e in node.iterable]
        for element in elements:
            value = element
            if len(node.target) > 1:
                # TODO Review this: must be tuple? (or can it be list too?)
                if len(node.target) > len(value._data):
                    raise Exception(f"ValueError: too many values to unpack (expected {len(node.target)})")
                for idx, t in enumerate(node.target):
                    if isinstance(t, Name):
                        self.scope.set(t.id, value._data[idx])       
            else:
                target = node.target[0]
                if isinstance(target, Name):
                    self.scope.set(target.id, value)
            for stmt in node.body:
                try:
                    self.visit(stmt)
                except Break:
                    return
                except Continue:
                    break

    def visit_While(self, node: While) -> None:
        while is_truthy(self.visit(node.condition)):
            for stmt in node.body:
                try:
                    self.visit(stmt)
                except Break:
                    return
                except Continue:
                    break

        # TODO: else on while

    def visit_Break(self, node: nodes.Break) -> Break:
        raise Break

    def visit_Continue(self, node: nodes.Continue) -> Continue:
        raise Continue

    def visit_Return(self, node: nodes.Return) -> Return:
        raise Return(self.visit(node.value))

    def visit_Pass(self, node: nodes.Pass) -> None:
        pass  # :)

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        self.visit(node.value)

    def visit_Compare(self, node: Compare) -> Value:
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)
        if isinstance(lhs, Value):
            left = lhs.value
        elif isinstance(lhs, (List, Tuple, Deque)):
            left = lhs._data
        elif isinstance(lhs, Dict):
            left = lhs._dict
        else:
            raise InterpreterError(f"Cannot do {lhs.repr()} {node.op!r} {rhs.repr()}")

        if isinstance(rhs, Value):
            right = rhs.value
        elif isinstance(rhs, (List, Tuple, Deque)):
            right = rhs._data
        elif isinstance(rhs, Dict):
            right = rhs._dict
        else:
            raise InterpreterError(f"Cannot do {lhs.repr()} {node.op!r} {rhs.repr()}")

        if node.op == "==":
            return Value(left == right)
        if node.op == "!=":
            return Value(left != right)
        if node.op == "<":
            return Value(left < right)
        if node.op == ">":
            return Value(left > right)
        if node.op == "<=":
            return Value(left <= right)
        if node.op == ">=":
            return Value(left >= right)
        if node.op == "in":
            if isinstance(right, str):
                return Value(left in right)
            if isinstance(right, (list, tuple, deque, dict)):
                return Value(
                    any(
                        isinstance(element, Value) and element.value == left
                        for element in right
                    )
                )
        if node.op == "not in":
            if isinstance(right, str):
                return Value(left not in right)
            if isinstance(right, (list, tuple, deque)):
                return Value(
                    not any(
                        isinstance(element, Value) and element.value == left
                        for element in right
                    )
                )
        if node.op == "is":
            return Value(left is right)
        if node.op == "is not":
            return Value(left is not right)

        raise NotImplementedError(node)

    def visit_BinOp(self, node: BinOp) -> Object:
        left = self.visit(node.left)
        right = self.visit(node.right)

        if not isinstance(left, Value) or not isinstance(right, Value):
            raise InterpreterError(
                f"Cannot perform {node.op} on a {type(left).__name__}"
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

    def visit_BoolOp(self, node: BoolOp) -> Object:
        left = self.visit(node.left)
        right = self.visit(node.right)

        if not isinstance(left, Value) or not isinstance(right, Value):
            raise InterpreterError(
                f"Cannot perform {node.op!r} on a {type(left).__name__!r}"
                f" and a {type(right).__name__!r}"
            )

        if node.op == "and":
            return Value(left.value and right.value)
        if node.op == "or":
            return Value(left.value or right.value)

        raise AssertionError(f"node.op must be 'and' or 'or', found {node.op!r}")

    def visit_UnaryOp(self, node: UnaryOp) -> Value:
        value = self.visit(node.value)
        if not isinstance(value, Value):
            raise InterpreterError(f"Cannot negate a {type(value).__name__!r}")

        if node.op == "not":
            return Value(not value.value)
        if node.op == "+":
            return value
        if node.op == "-":
            return Value(-value.value)

        raise AssertionError(f"node.op must be '+', '-', or 'not', found {node!r}")

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

        if isinstance(node.key, Slice):
            if isinstance(obj, Value) and isinstance(obj.value, str):
                start = self.visit(node.key.start)
                end = self.visit(node.key.end)
                if not (
                    isinstance(start, Value)
                    and isinstance(end, Value)
                    and (start.value is None or isinstance(start.value, int))
                    and (end.value is None or isinstance(end.value, int))
                ):
                    raise InterpreterError(
                        f"Slice indices should be integers or 'None', got {start.repr()}, {end.repr()}"
                    )
                return Value(obj.value[start.value : end.value])
            raise NotImplementedError(node)

        key = self.visit(node.key)
        if isinstance(obj, (List, Tuple, Deque)):
            if not (isinstance(key, Value) and isinstance(key.value, int)):
                raise InterpreterError(
                    f"{type(obj).__name__} indices should be integers, got {key.repr()}"
                )
            return obj._data[key.value]
        if isinstance(obj, Dict) and key in obj._dict:
            return obj._dict[key]
        if (
            isinstance(obj, Value)
            and isinstance(obj.value, str)
            and isinstance(key, Value)
        ):
            return Value(obj.value[key.value])
        if (
            isinstance(obj, Value)
            and isinstance(obj.value, bytes)
            and isinstance(key, Value)
        ):
            return Value(obj.value[key.value])

        raise InterpreterError(f"{type(obj).__name__} object has no key {key.repr()}")

    def visit_Attribute(self, node: Attribute) -> Object:
        attribute_name = node.attr
        obj = self.visit(node.value)
        assert obj is not None

        if attribute_name in obj.attributes:
            return obj.attributes[attribute_name]

        if attribute_name in obj.methods:
            return obj.methods[attribute_name]

        raise InterpreterError(
            f"{type(obj).__name__} object has no attribute {attribute_name!r}"
        )

    def visit_Name(self, node: Name) -> Value:
        name = node.id

        current_scope = self.scope
        while current_scope is not None:
            value = current_scope.get(name)
            if value is NOT_SET:
                current_scope = current_scope.parent
            else:
                return value

        value = self.globals.get(name)
        if value is NOT_SET:
            raise InterpreterError(f"{name!r} is not defined")

        return value

    def visit_List(self, node: nodes.List) -> List:
        elements = [self.visit(element) for element in node.elements]
        return List(elements)

    def visit_Tuple(self, node: nodes.Tuple) -> Tuple:
        elements = [self.visit(element) for element in node.elements]
        return Tuple(elements)

    def visit_Dict(self, node: nodes.Dict) -> Dict:
        keys = [self.visit(key) for key in node.keys]
        values = [self.visit(value) for value in node.values]
        return Dict(keys, values)

    def visit_Constant(self, node: Constant) -> Value:
        return Value(node.value)


def interpret(source: str) -> None:
    module = parse(source)
    if module is None:
        return

    Interpreter().visit(module)


def main() -> None:
    source = sys.stdin.read()
    module = interpret(source)
    if module is None:
        return

    if "--pretty" in sys.argv:
        try:
            import black
        except ImportError:
            print("Error: `black` needs to be installed for `--pretty` to work.")

        print(black.format_str(repr(module), mode=black.Mode()))
    else:
        print(module)


if __name__ == "__main__":
    main()