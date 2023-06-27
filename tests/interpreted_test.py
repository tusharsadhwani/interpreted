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
            print(x.popleft())
            y = x.popleft()
            print(y)
            """,
            "5\n6\n",
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
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    assert process.stdout.decode() == output
    assert process.stderr == b""


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
