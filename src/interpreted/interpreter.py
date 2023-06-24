from interpreted.nodes import Call, ExprStmt, Module, Name, Node
from interpreted.parser import parse


class Interpreter:
    def visit(self, node: Node) -> None:
        node_type = type(node).__name__
        visitor_method = getattr(self, f"visit_{node_type}", None)
        if visitor_method is None:
            return  # TODO: delete this

        visitor_method(node)

        children = []
        for field in node.__dataclass_fields__:
            child = getattr(node, field)

            if isinstance(child, Node):
                children.append(child)
            elif isinstance(child, list):
                children.extend(item for item in child if isinstance(item, Node))

        for child in children:
            self.visit(child)

    def visit_Module(self, node: Module) -> None:
        ...

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        ...

    def visit_Call(self, node: Call) -> None:
        if isinstance(node.function, Name):
            print(node.function.id)


def interpret(source: str) -> None:
    module = parse(source)
    if module is None:
        return

    Interpreter().visit(module)
