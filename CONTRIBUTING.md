# Contributing

Thank you for considering a contribution to MyJev.

## Setup

Python 3.10 or newer is required. Use [uv](https://docs.astral.sh/uv/) for local development:

```bash
uv sync
```

The default environment is sufficient for the OpenAI-compatible backend and tests. Local model backends have separate extras documented in the README.

## Workflow

1. Open or comment on an issue for a behavioral change before sending a large patch.
2. Create a focused branch and keep unrelated formatting out of the change.
3. Add or update tests for changed behavior.
4. Run the checks below.
5. Open a pull request with the motivation, user-visible change, and verification commands.

## Checks

Run the complete test suite before submitting:

```bash
python -m unittest discover -s tests -v
```

Also check syntax:

```bash
python -m compileall -q src tests
```

If a change affects packaging, run:

```bash
uv build
```

## Reporting issues

For bugs, include the Python version, operating system, backend, minimal request, expected result, actual result, and full traceback. Remove secrets and private data. For security issues, see [SECURITY.md](SECURITY.md).
