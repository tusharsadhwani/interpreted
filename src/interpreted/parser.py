from __future__ import annotations
from keyword import iskeyword

import sys

from interpreted.tokenizer import Token, TokenType, index_to_line_column, tokenize
from interpreted.nodes import (
    Assign,
    Attribute,
    AugAssign,
    BinOp,
    BoolOp,
    Break,
    Call,
    Compare,
    Constant,
    Continue,
    Dict,
    ExprStmt,
    Expression,
    For,
    FunctionDef,
    If,
    List,
    Module,
    Name,
    Pass,
    Return,
    Statement,
    Subscript,
    Tuple,
    UnaryOp,
    While,
)


class ParseError(Exception):
    def __init__(self, msg: str, index: int) -> None:
        super().__init__(msg)
        self.index = index


class Parser:
    r"""
    Current grammar:
        Module -> Statement*
        Statement -> single_line_stmt | multi_line_stmt
        multi_line_stmt -> FunctionDef | If | While | For
        FunctionDef -> 'def' NAME '(' params? ')' ':' block
        params -> NAME (',' NAME)*
        block -> NEWLINE INDENT Statement* DEDENT | single_line_stmt
        If -> 'if' expression ':' block elif
            | 'if' expression ':' block else?
        elif -> 'elif' expression ':' block elif
              | 'elif' expression ':' block else?
        else -> 'else' ':' block
        While -> 'while' expression ':' block [else]
        For -> 'for' targets 'in' expressions ':' block else?
        targets -> primary (',' primary)* ','?
        single_line_stmt -> Pass | Break | Continue | Return | Assign | ExprStmt
        Pass -> 'pass' '\n'
        Return -> 'return' expressions? '\n'
        expressions -> expression (',' expression)* ','?
        Assign -> targets '=' Assign | expressions
        ExprStmt -> expressions '\n'

        expression -> logical_or
        logical_or -> logical_and ('or' logical_and)*
        logical_and -> logical_not ('and' logical_not)*
        logical_not -> 'not' logical_not | comparison
        comparison -> sum (('>' | '>=' | '<' | '<=' | '==' | '!=' | 'in' | 'not' 'in') sum)*
        # can also be written as:
        # sum -> factor ('+' factor)* | factor ('-' factor)* | factor
        sum -> sum '+' factor | sum '-' factor | factor
        term -> factor '*' unary
              | factor '/' unary
              | factor '//' unary
              | factor '%' unary
              | factor '@' unary
              | unary
        unary -> '+' unary | '-' unary | '~' unary | power
        power -> primary '**' unary

        primary -> Attribute
                 | Subscript
                 | Call
                 | literal
        Attribute -> primary '.' NAME
        Subscript -> primary '[' expression ']'
        Call -> primary '(' arguments? ')'
        arguments -> expression (',' expression)*
        literal -> NUMBER
                 | NAME
                 | STRING
                 | 'True'
                 | 'False'
                 | 'None'
                 | List
                 | Tuple
                 | Dict
        List -> '[' expressions ']'
        Tuple -> '(' expression ',' expressions? ')'
        Dict -> '{' (expression ':' expression)* ','? ']'
    """

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def parsed(self) -> bool:
        return self.index >= len(self.tokens)

    def advance(self) -> None:
        self.index += 1

    def current(self) -> Token | None:
        if self.parsed:
            return None

        return self.tokens[self.index - 1]

    def peek(self) -> Token | None:
        if self.parsed:
            return None

        return self.tokens[self.index]

    def peek_next(self) -> Token | None:
        if self.index + 1 >= len(self.tokens):
            return None

        return self.tokens[self.index + 1]

    def match_type(self, token_type: TokenType) -> bool:
        if self.parsed:
            return False

        token = self.peek()
        if token.token_type != token_type:
            return False

        self.advance()
        return True

    def match_name(self, *names: str) -> bool:
        if self.parsed:
            return False

        token = self.peek()
        if token.token_type != TokenType.NAME or token.string not in names:
            return False

        self.advance()
        return True

    def match_op(self, *ops: str) -> bool:
        if self.parsed:
            return False

        token = self.peek()
        if token.token_type != TokenType.OP or token.string not in ops:
            return False

        self.advance()
        return True

    def expect(self, token_type: TokenType) -> None:
        if self.parsed:
            raise ParseError(f"Expected {token_type}, found EOF", self.index)

        if not self.match_type(token_type):
            token = self.peek()
            raise ParseError(
                f"Expected {token_type}, found {token.token_type}", self.index
            )

    def expect_op(self, op: str) -> None:
        if self.parsed:
            raise ParseError(f"Expected {op}, found EOF", self.index)

        if not self.match_op(op):
            token = self.peek()
            raise ParseError(f"Expected '{op}', found '{token.string}'", self.index)

    def parse(self) -> Module:
        statements: list[Statement] = []
        while not self.parsed:
            statement = self.parse_statement()
            statements.append(statement)

        return Module(body=statements)

    def parse_statement(self) -> Statement:
        # Extra newlines can be ignored as empty statements
        while self.match_type(TokenType.NEWLINE):
            pass

        if self.match_name("def", "if", "for", "while"):
            return self.parse_multiline_statement()
        else:
            return self.parse_single_line_statement()

    def parse_multiline_statement(self) -> FunctionDef | For | If | While:
        keyword = self.current().string
        if keyword == "def":
            return self.parse_function_def()

        if keyword == "if":
            return self.parse_if()

        if keyword == "while":
            return self.parse_while()

        # TODO: for
        raise NotImplementedError()

    def parse_function_def(self) -> FunctionDef:
        self.expect(TokenType.NAME)
        function_name = self.current().string
        self.expect_op("(")

        # special case: function just closes
        if self.match_op(")"):
            params = []
        else:
            self.expect(TokenType.NAME)
            first_param = self.current().string
            params = [first_param]

            while not self.match_op(")"):
                # every new arg must be preceded by a comma
                self.expect_op(",")
                self.expect(TokenType.NAME)
                param = self.current().string
                params.append(param)

                # TODO: trailing comma support

        self.expect_op(":")
        body = self.parse_body()
        return FunctionDef(name=function_name, params=params, body=body)

    def parse_if(self) -> If:
        condition = self.parse_expression()
        self.expect_op(":")
        body = self.parse_body()

        orelse = []
        if self.match_name("elif"):
            orelse = self.parse_if()

        elif self.match_name("else"):
            self.expect_op(":")
            orelse = self.parse_body()

        return If(condition=condition, body=body, orelse=orelse)

    def parse_while(self) -> While:
        condition = self.parse_expression()
        self.expect_op(":")

        body = self.parse_body()

        orelse = []
        if self.match_name("else"):
            self.expect_op(":")
            orelse = self.parse_body()

        return While(condition=condition, body=body, orelse=orelse)

    def parse_body(self) -> list[Statement]:
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)

        body = []
        while True:
            statement = self.parse_statement()
            body.append(statement)
            if self.parsed or self.match_type(TokenType.DEDENT):
                break

        return body

    def parse_single_line_statement(
        self,
    ) -> Pass | Break | Continue | Return | Assign | ExprStmt:
        if self.match_name("pass"):
            self.expect(TokenType.NEWLINE)
            return Pass()

        if self.match_name("break"):
            self.expect(TokenType.NEWLINE)
            return Break()

        if self.match_name("continue"):
            self.expect(TokenType.NEWLINE)
            return Continue()

        elif self.match_name("return"):
            return_values = self.parse_expressions()
            # TODO: make it a tuple if > 1
            assert len(return_values) == 1
            self.expect(TokenType.NEWLINE)
            return Return(value=return_values[0])

        # Now here we come to a conundrum.
        # Assign expects `targets`, and ExprStmt expects `expressions`, and `targets`
        # is a restricted version of `expressions`.
        # Trying to parse an assignment, but then failing would mean that you have to
        # backtrack and re-try with `expressions`.
        # But, I don't want to do all the backtrack logic.
        # So we compromise. Instead we parse the `targets` part as an expression, and
        # then check if it is followed by an `=`, if it is then we see if it's a valid
        # target or not, and fail or proceed accordingly.
        else:
            return self.parse_assign_or_exprstmt()

    def parse_assign_or_exprstmt(self) -> Assign | ExprStmt:
        expressions = self.parse_expressions()

        next_token = self.peek()
        if next_token.token_type != TokenType.OP:
            self.expect(TokenType.NEWLINE)
            if len(expressions) == 1:
                value = expressions[0]
            else:
                value = Tuple(expressions)

            return ExprStmt(value=value)

        if self.match_op(
            "+=",
            "-=",
            "*=",
            "@=",
            "/=",
            "%=",
            "&=",
            "|=",
            "^=",
            "**=",
        ):
            assert_expressions_are_targets(expressions, self.index)
            if len(expressions) != 1:
                raise ParseError(
                    "Augmented assignment only works with a single target", self.index
                )

            target = expressions[0]
            value = self.parse_expression()
            self.expect(TokenType.NEWLINE)
            return AugAssign(target=target, op=next_token.string, value=value)

        if next_token.string != "=":
            raise ParseError(f"Expected '=', found '{next_token.string}'", self.index)

        # Now since we know the next token is a `=`, we parse an Assign node
        assign_targets = []
        while self.match_op("="):
            assert_expressions_are_targets(expressions, self.index)

            # TODO: make them a tuple if > 1
            assert len(expressions) == 1
            assign_targets.append(expressions[0])
            expressions = self.parse_expressions()

        self.expect(TokenType.NEWLINE)
        # TODO: make them a tuple if > 1
        assert len(expressions) == 1
        return Assign(targets=assign_targets, value=expressions[0])

    def parse_expressions(self) -> list[Expression]:
        expressions = [self.parse_expression()]
        while self.match_op(","):
            expression = self.parse_expression()
            expressions.append(expression)

        # TODO: trailing comma support
        return expressions

    def parse_expression(self) -> Expression:
        # TODO: extraneous parens can be parsed here.
        return self.parse_or()

    def parse_or(self) -> Expression:
        left = self.parse_and()
        while self.match_name("or"):
            right = self.parse_and()
            left = BoolOp(left=left, op="or", right=right)

        return left

    def parse_and(self) -> Expression:
        left = self.parse_not()
        while self.match_name("and"):
            right = self.parse_not()
            left = BoolOp(left=left, op="and", right=right)

        return left

    def parse_not(self) -> Expression:
        if self.match_name("not"):
            return UnaryOp(value=self.parse_not(), op="not")

        return self.parse_comparison()

    def parse_comparison(self) -> Expression:
        left = self.parse_sum()
        while True:
            if self.match_op("<", ">", "<=", ">=", "==", "!="):
                operator = self.current().string
            elif self.match_name("in", "is"):
                operator = self.current().string
            elif self.peek().string == "is" and self.peek_next().string == "not":
                self.advance()
                self.advance()
                operator = self.current().string
            elif self.peek().string == "not" and self.peek_next().string == "in":
                self.advance()
                self.advance()
                operator = self.current().string
            else:
                break

            operator = self.current().string
            right = self.parse_sum()
            left = Compare(left=left, op=operator, right=right)

        return left

    def parse_sum(self) -> Expression:
        left = self.parse_factor()
        while self.match_op("+", "-"):
            operator = self.current().string
            right = self.parse_factor()
            left = BinOp(left=left, op=operator, right=right)

        return left

    def parse_factor(self) -> Expression:
        left = self.parse_unary()
        while self.match_op("*", "/", "//", "%", "@"):
            operator = self.current().string
            right = self.parse_unary()
            left = BinOp(left=left, op=operator, right=right)

        return left

    def parse_unary(self) -> Expression:
        if self.match_op("~", "+", "-"):
            operator = self.current().string
            return UnaryOp(value=self.parse_unary(), op=operator)

        return self.parse_power()

    def parse_power(self) -> Expression:
        left = self.parse_primary()
        while self.match_op("**"):
            operator = self.current().string
            right = self.parse_unary()
            left = BinOp(left=left, op=operator, right=right)

        return left

    def parse_primary(self) -> Expression:
        primary = self.parse_literal()

        while True:
            if self.match_op("."):
                self.expect(TokenType.NAME)
                attrname = self.current().string
                primary = Attribute(value=primary, attr=attrname)

            elif self.match_op("["):
                key = self.parse_expression()
                self.expect_op("]")
                primary = Subscript(value=primary, key=key)

            elif self.match_op("("):
                # edge case: no args
                if self.match_op(")"):
                    args = []
                else:
                    args = self.parse_expressions()
                    self.expect_op(")")

                primary = Call(function=primary, args=args)

            else:
                break

        return primary

    def parse_literal(self) -> Expression:
        if self.match_type(TokenType.NAME):
            token = self.current()
            if token.string in ("True", "False", "None") or not iskeyword(token.string):
                if token.string == "True":
                    return Constant(True)
                if token.string == "False":
                    return Constant(False)
                if token.string == "None":
                    return Constant(None)

                return Name(token.string)

            else:
                raise ParseError(f"Unexpected keyword {token.string!r}", self.index - 1)

        if self.match_type(TokenType.NUMBER):
            token = self.current()
            if token.string.isdigit():
                return Constant(int(token.string))
            else:
                return Constant(float(token.string))

        if self.match_type(TokenType.STRING):
            token = self.current()
            return Constant(unquote(token.string))

        if self.match_op("("):
            # special_case: no items
            if self.match_op(")"):
                return Tuple(elements=[])

            elements = self.parse_expressions()
            self.expect_op(")")
            return Tuple(elements)

        if self.match_op("["):
            # special_case: no items
            if self.match_op("]"):
                return List(elements=[])

            elements = self.parse_expressions()
            self.expect_op("]")
            return List(elements)

        if self.match_op("{"):
            # special_case: no items
            if self.match_op("}"):
                return Dict(keys=[], values=[])

            keys = [self.parse_expression()]
            self.expect_op(":")
            values = [self.parse_expression()]
            while self.match_op(","):
                keys.append(self.parse_expression())
                self.expect_op(":")
                values.append(self.parse_expression())

            # TODO: trailing comma support
            self.expect_op("}")
            return Dict(keys=keys, values=values)

        raise ParseError(f"Unexpected token {self.peek().string!r}", self.index)


def assert_expressions_are_targets(expressions: list[Expression], index) -> None:
    for target in expressions:
        if not isinstance(target, (Name, Subscript)):
            node_type = type(target).__name__
            raise ParseError(f"Cannot assign to a {node_type}", index)


def unquote(string: str) -> str:
    if string.startswith('"""'):
        assert string.endswith('"""')
        return string[3:-3]

    if string.startswith("'''"):
        assert string.endswith("'''")
        return string[3:-3]

    if string.startswith('"'):
        assert string.endswith('"')
        return string[1:-1]

    if string.startswith("'"):
        assert string.endswith("'")
        return string[1:-1]

    raise ValueError(f"Unknown string format: {string}")


def parse(source: str) -> Module | None:
    tokens = tokenize(source)
    if tokens is None:
        return None

    try:
        return Parser(tokens).parse()

    except ParseError as exc:
        token = tokens[exc.index]
        line, column = index_to_line_column(token.start, source)
        print(f"Parse Error at {line}:{column} -", exc)
        return


def main() -> None:
    source = sys.stdin.read()
    module = parse(source)
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
