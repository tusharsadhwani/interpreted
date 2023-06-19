from __future__ import annotations
from keyword import iskeyword

import sys

from interpreted.tokenizer import (
    Token,
    TokenType,
    TokenizeError,
    Tokenizer,
    index_to_line_column,
)
from interpreted.nodes import (
    Assign,
    AugAssign,
    Call,
    Compare,
    Constant,
    ExprStmt,
    Expression,
    For,
    If,
    Module,
    Name,
    Pass,
    Return,
    Statement,
    Subscript,
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
        elif -> 'elif' expression ':' block elif_stmt
              | 'elif' expression ':' block else?
        else -> 'else' ':' block
        While -> 'while' expression ':' block [else]
        For -> 'for' targets 'in' ~ star_expressions ':' [TYPE_COMMENT] block [else_block]
        targets -> primary (',' primary )* ','?
        single_line_stmt -> Pass | Return | Assign | ExprStmt
        Pass -> 'pass' '\n'
        Return -> 'return' expressions? '\n'
        expressions -> expression (',' expression )* ','?
        Assign -> targets '=' Assign | expressions
        ExprStmt -> expressions '\n'

        expression -> logical_or
        logical_or -> logical_and ('or' logical_and)*
        logical_and -> logical_not ('and' logical_not)*
        logical_not -> 'not' logical_not | comparison
        comparison -> sum (('>' | '>=' | '<' | '<=') sum)*
        sum -> sum '+' term | sum '-' term | term
        term -> term '*' factor
              | term '/' factor
              | term '//' factor
              | term '%' factor
              | term '@' factor
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
        return self.index >= len(self.tokens) - 1

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

    def parse_multiline_statement(self) -> For | If | While:
        keyword = self.current().string
        if keyword == "if":
            return self.parse_if()

        if keyword == "while":
            return self.parse_while()

        # TODO: for
        raise NotImplementedError()

    def parse_if(self) -> If:
        condition = self.parse_expression()
        self.expect_op(":")
        self.expect(TokenType.NEWLINE)

        body = self.parse_body()
        # TODO: else
        if self.match_name("else"):
            raise NotImplementedError()

        return If(condition=condition, body=body, orelse=[])

    def parse_while(self) -> While:
        condition = self.parse_expression()
        self.expect_op(":")
        self.expect(TokenType.NEWLINE)

        body = self.parse_body()
        # TODO: else
        if self.match_name("else"):
            raise NotImplementedError()

        return While(condition=condition, body=body, orelse=[])

    def parse_body(self) -> list[Statement]:
        self.expect(TokenType.INDENT)

        body = []
        while True:
            statement = self.parse_statement()
            body.append(statement)
            if self.parsed or self.match_type(TokenType.DEDENT):
                break

        return body

    def parse_single_line_statement(self) -> Pass | Return | Assign | ExprStmt:
        if self.match_name("pass"):
            self.expect(TokenType.NEWLINE)
            return Pass()

        elif self.match_name("return"):
            return_value = self.parse_expressions()
            self.expect(TokenType.NEWLINE)
            return Return(value=return_value)

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
            # TODO: make a tuple
            assert len(expressions) == 1
            return ExprStmt(value=expressions[0])

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

    def parse_expression(self) -> Expression:
        # TODO: the entire expression ladder
        return self.parse_comparison()

    def parse_expressions(self) -> list[Expression]:
        # TODO: parse a comma sepratated list of expressions.
        return [self.parse_comparison()]

    def parse_comparison(self) -> Expression:
        primary = self.parse_primary()
        if not self.match_op("<", ">", "<=", ">=", "==", "!="):
            return primary

        left = primary
        operator = self.current().string
        right = self.parse_primary()
        return Compare(left=left, op=operator, right=right)

    def parse_primary(self) -> Expression:
        primary = self.parse_literal()

        while True:
            # TODO: attributes and subscripts
            if self.match_op("."):
                raise NotImplementedError()

            elif self.match_op("["):
                raise NotImplementedError()

            elif self.match_op("("):
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
                    value = True
                elif token.string == "False":
                    value = False
                elif token.string == "None":
                    value = None
                else:
                    value = token.string

                return Name(value)

            else:
                raise ParseError("Unexpected keyword", self.index)

        if self.match_type(TokenType.NUMBER):
            token = self.current()
            if token.string.isdigit():
                return Constant(int(token.string))
            else:
                return Constant(float(token.string))

        if self.match_type(TokenType.STRING):
            token = self.current()
            return Constant(unquote(token.string))

        raise NotImplementedError()


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


def main() -> None:
    source = sys.stdin.read()

    try:
        tokens = Tokenizer(source).scan_tokens()
    except TokenizeError as exc:
        line, column = index_to_line_column(exc.index, source)
        print(f"Tokenize Error at {line}:{column} -", exc)
        return

    try:
        module = Parser(tokens).parse()
    except ParseError as exc:
        token = tokens[exc.index]
        line, column = index_to_line_column(token.start, source)
        print(f"Parse Error at {line}:{column} -", exc)
        return

    print(module)


if __name__ == "__main__":
    main()
