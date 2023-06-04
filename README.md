# interpreted

A Python interpreter, written from scratch in Python.

This interpreter is made solely as the base for my talk,
"Writing a Python interpreter from scratch, in half an hour."

## Installation

```bash
pip install interpreted
```

## Usage

```console
$ cat foo.py
print("2 + 2 is", 2 + 2)

def greet(name='User'):
	print('Hello,', name + '!')

greet()

$ interpreted foo.py
2 + 2 is 4
Hello, User!
```

## Local Development / Testing

- Create and activate a virtual environment
- Run `pip install -r requirements-dev.txt` to do an editable install
- Run `pytest` to run tests

## Type Checking

Run `mypy .`

## Create and upload a package to PyPI

Make sure to bump the version in `setup.cfg`.

Then run the following commands:

```bash
rm -rf build dist
python setup.py sdist bdist_wheel
```

Then upload it to PyPI using [twine](https://twine.readthedocs.io/en/latest/#installation):

```bash
twine upload dist/*
```
