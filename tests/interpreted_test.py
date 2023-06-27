import subprocess
import tempfile

from textwrap import dedent

import pytest


@pytest.mark.parametrize(
    ("source", "output"),
    (
        ("print('hello!')\n", "hello!\n"),
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
            "[5, 6] 2\n[foo, 10, bar] 3\n",
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
    assert process.stdout.decode() == output


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
