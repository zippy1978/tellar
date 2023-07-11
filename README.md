# Tellar

Talk to your favortie fictional characters.

## Installation

Python 3.10+ is required.

Install with:

```bash
$ pip3 install tellar@git+https://github.com/zippy1978/tellar
```

## Usage

An OpenAI API key is required to used the tool.

Export it as an environement variable:

```bash
$ export OPENAI_API_KEY=your-key
```

```bash
$ tellar --help
Usage: tellar [OPTIONS]

Options:
  -c, --character TEXT  character name  [required]
  -p, --pdf TEXT        book PDF file path  [required]
  -l, --language TEXT   language  [default: english]
  -d, --debug           debug mode
  --help                Show this message and exit.
```

## Development environement setup

A venv is recommended to run the project properly (see https://docs.python.org/fr/3/library/venv.html).

### Install dependencies

```bash
$ export HNSWLIB_NO_NATIVE=1
$ poetry install
```