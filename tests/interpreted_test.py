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
            x = 5

            def bar():
                x = 10

                def baz():
                    def foo():
                        print(x)

                    return foo

                return baz

            foo = bar()()
            foo()
            """,
            "10\n",
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
        ),
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

@pytest.mark.parametrize(
    ("source", "output"),
    (
        (
            """\
            for e in [1,2]:
                print(e)
            """, 
            "1\n2\n"
        ),
        (
            """\
            lst = ['test','test123']
            for e in lst:
                print(e)
            """,
            "test\ntest123\n"
        ),
        (
            """\
            for x in 1, 2:
                print(x)
            """,
            "1\n2\n"
        ),
        (
            """\
            dct = { "one": 1, "two": 2 }
            for k in dct:
                print(k, dct[k])
            """,
            "one 1\ntwo 2\n"
        ),
        (
            """\
            dct = { "one": 1, "two": 2 }
            for k,v in dct.items():
                print(k, v)
            """,
            "one 1\ntwo 2\n"
        ),
        (
            """\
            dct = { "one": 1, "two": 2 }
            for k in dct.items():
                print(k)
            """,
            "('one', 1)\n('two', 2)\n"
        ),
        (
            """\
            dct = { "one": 1, "two": 2 }
            for idx, tup in enumerate(dct):
                print(idx, tup)
            """,
            "0 one\n1 two\n"
        ),
    ),
)
def test_for(source, output) -> None:
    """Tests the interpreter CLI."""
    with tempfile.NamedTemporaryFile("w+") as file:
        file.write(dedent(source))
        file.seek(0)
        
        process = subprocess.run(
            ["interpreted", file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # also test real python output
        # TODO this gives a lot of coverage warnings
        file.seek(0)
        process2 = subprocess.run(
            ["python", file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  
        )

    assert process2.stdout.decode() == dedent(output)
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


def test_imports(tmp_path) -> None:
    math_content = """\
        PI = 3.14

        def add(a, b):
            return a + b

        def mul(a, b):
            return a * b

        def area(r):
            return PI * r * r
    """
    smth_content = """\
        from calc import *
        def add2():
            return add(2, 2)
    """
    utils_content = """\
        import smth as math

        def cos(x):
            print(math.add2())
            return "bru what"
    """
    main_content = """\
        from utils import math, cos
        import smth

        print(math.area(2))
        print(math.add(2,3))
        print(math.mul(3,4))
        print(cos(30))
    """

    main = tmp_path / "main.py"
    main.write_text(dedent(main_content))

    utils = tmp_path / "utils.py"
    utils.write_text(dedent(utils_content))

    math = tmp_path / "calc.py"
    math.write_text(dedent(math_content))

    smth = tmp_path / "smth.py"
    smth.write_text(dedent(smth_content))

    process = subprocess.run(
        ["interpreted", main.as_posix()],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path),
    )

    assert process.stderr == b""
    assert process.stdout.decode() == "12.56\n5\n12\n4\nbru what\n"
    assert process.returncode == 0
