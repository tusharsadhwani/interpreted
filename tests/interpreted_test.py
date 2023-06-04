import subprocess
import tempfile


def test_interpret() -> None:
    """Tests the interpreter CLI."""
    with tempfile.NamedTemporaryFile() as file:
        file.write(b"print('hello!')\n")
        file.seek(0)

        process = subprocess.run(
            ["interpreted", file.name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    assert process.stdout == b"hello!\n"
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
