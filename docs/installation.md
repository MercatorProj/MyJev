# Installation

[简体中文](installation_zh.md) · [Back to README](../README.md)

Clone the repository:

```bash
git clone https://github.com/MercatorProj/MyJev.git
cd MyJev
```

Python 3.10 or newer is required.

## OpenAI-compatible API

The default installation is sufficient for the OpenAI-compatible backend:

```bash
uv sync
```

Set the API connection before running an example:

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
```

PowerShell uses `$env:OPENAI_BASE_URL` and `$env:OPENAI_API_KEY` instead.

## Transformers backend

For a local Transformers backend:

```bash
uv sync --extra transformers
```

Pip users can use:

```bash
python -m pip install -e ".[transformers]"
```

## SGLang backend

SGLang is intended for Linux with a supported NVIDIA GPU:

```bash
uv sync --extra sglang
source .venv/bin/activate
```

Pip users can use:

```bash
python -m pip install -e ".[sglang]"
```

After installation, see the [Usage guide](usage.md) to run Python examples or start the HTTP service.
