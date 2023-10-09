import subprocess
import tempfile
from textwrap import dedent

import pytest


@pytest.mark.parametrize(
    ("source", "output"),
    (
        ("print('hello!')", "hello!\n"),
        ('print("""foo""")', "foo\n"),
        (r"print('foo \x41 bar')", "foo A bar\n"),
        (r"print('foo \u1234 bar')", "foo ሴ bar\n"),
        (r"print('foo \u2603 bar')", "foo ☃ bar\n"),
        (r"print('foo \U00002603 bar')", "foo ☃ bar\n"),
        (r"print('foo \U0001F643 bar')", "foo 🙃 bar\n"),
        (r"print('foo \x41 \U0001F643 bar')", "foo A 🙃 bar\n"),
        (
            """\
            a = b'abc'
            print(a)
            print(a[0])
            print(a * 2)
            print(a + b'd')
            """,
            """\
            b'abc'
            97
            b'abcabc'
            b'abcd'
            """,
        ),
        (
            """\
            def foo(x):
                y = 5
                print(x, y)

            foo("hi")
            """,
            "hi 5\n",
        ),
        (
            """\
            x = deque()
            x.append(5)
            x.append(6)
            print(len(x))
            print(x.popleft())
            y = x.popleft()
            print(y, len(x))
            """,
            "2\n5\n6 0\n",
        ),
        (
            """\
            x = []
            x.append(5)
            x.append(6)
            print(x, len(x))
            y = ["foo", 10, "bar"]
            print(y, len(y))
            """,
            "[5, 6] 2\n['foo', 10, 'bar'] 3\n",
        ),
        (
            """\
            x = "abc"
            print(x[:1])
            print(x[1:])
            print(x[:-1])
            print(x[:])
            print(x[1:2])
            """,
            "a\nbc\nab\nabc\nb\n",
        ),
        (
            """\
            def foo(func):    
                print('inside decorator')
                return func

            @foo
            def xyz():
                print('inside xyz')

            xyz()
            """, 
            "inside decorator\ninside xyz\n",
        ), 
        (
            """\
            def decorator_foo(func):
                print('Inside decorator foo')
                return func

            def ab5(func):  
                print('Inside decorator bar')
                return func

            @decorator_foo
            @ab5
            def xyz():
                print('Inside xyz')

            xyz()
            """, 
            "Inside decorator bar\nInside decorator foo\nInside xyz\n",
        ),
        (
            """\
            def decorator_foo(func):
                print('Inside decorator foo')
                return func

            def ab5(func):  
                print('Inside decorator bar')
                def wrapper():
                    print('Inside wrapper')
                    return func()
                return wrapper

            @decorator_foo
            @ab5
            def xyz():
                print('Inside xyz')

            xyz()
            """, 
            "Inside decorator bar\nInside decorator foo\nInside wrapper\nInside xyz\n",
        )
    ),
)
def test_interpret(source, output) -> None:
    """Tests the interpreter CLI."""
    with tempfile.NamedTemporaryFile("w+") as file:
        file.write(dedent(source))
        file.seek(0)

        process = subprocess.run(
            ["interpreted", file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    assert process.stderr == b""
    assert process.stdout.decode() == dedent(output)


def test_file_not_found() -> None:
    """Tests the file not found prompt."""
    process = subprocess.run(
        ["interpreted", "foo.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout == b""
    assert process.stderr == b"\x1b[31mError:\x1b[m Unable to open file: 'foo.py'\n"
    assert process.returncode == 1
