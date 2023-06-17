from __future__ import annotations
import json

import sys

from interpreted.tokenizer import Token, Tokenizer
from interpreted.nodes import Module


class Parser:
    r"""
    Current grammar:
        Module -> Statement*
        Statement -> single_line_stmt | multi_line_stmt
        multi_line_stmt -> FunctionDef | If | While | For
        single_line_stmt -> Pass | Assign | Return | ExprStmt
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
        Return -> 'return' expressions? '\n'
        expressions -> expression (',' expression )* ','?
        ExprStmt -> expression '\n'
        Assign -> targets '=' Assign | logical_or
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
        primary -> primary '.' NAME
                 | primary '[' expression ']'
                 | primary '(' arguments? ')'
                 | literal
        arguments -> expression (',' expression)*
        literal -> NUMBER
                 | NAME
                 | STRING
                 | 'True'
                 | 'False'
                 | 'None'
                 | List
                 | Dict
        List -> '[' expressions ']'
        Dict -> '{' (expression ':' expression)* ','? ']'
    """

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def parsed(self) -> int:
        return self.index >= len(self.tokens) - 1

    def advance(self) -> None:
        self.index += 1

    def get_token(self) -> Token | None:
        if self.parsed:
            return None

        return self.tokens[self.index]

    def parse(self) -> Module:
        while not self.parsed:
            token = self.get_token()


if __name__ == "__main__":
    print(
        json.dumps(
            Parser(Tokenizer(sys.stdin.read()).scan_tokens()),
            default=vars,
            indent=2,
        )
    )
