  <p align="center">
    <img src="assets/myjev-banner.jpeg" alt="MyJev" width="100%">
  </p>

# MyJev

[简体中文](README_zh.md)

[![Tests](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml/badge.svg)](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml)

**MyJev is a lightweight Jev wrapper for language models.** It turns runtime-defined `Choice`, `Score`, and `Noul` questions into prefill-only yes/no judgments, then returns typed answers with normalized probabilities.

The design is inspired by [LLM2Jev](https://github.com/Yinsongxu/LLM2Jev). MyJev independently implements that idea as a small Python layer around existing model APIs and runtimes. It does not train, fine-tune, host, or modify models.

MyJev is an independent open-source project. It is not affiliated with or endorsed by Jev, TypeSafe, or the LLM2Jev authors.

## Why MyJev

- Keep the request schema compact: express options and levels directly in a `JevRequest`.
- Avoid free-form generation and ad hoc JSON parsing for structured decisions.
- Use an existing OpenAI-compatible API when only logprob access is needed.
- Use SGLang for high-throughput local inference and shared-prefix reuse.

Python 3.10 or newer is required.

## Install

The package is currently installed from source:

```bash
git clone https://github.com/MercatorProj/MyJev.git
cd MyJev
python -m pip install -e .
```

Optional backend extras:

```bash
python -m pip install -e ".[transformers]"
python -m pip install -e ".[sglang]"
```

`sglang` is intended for Linux with a supported NVIDIA GPU.

## Model API quick start

Set the endpoint and key:

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
```

PowerShell uses:

```powershell
$env:OPENAI_BASE_URL = "https://your-openai-compatible-service/v1"
$env:OPENAI_API_KEY = "your-api-key"
```

Then run the bundled example:

```bash
python examples/openai_compatible_inference.py --model your-model-name
```

The API must return first-token top logprobs containing both `yes` and `no`. Since providers expose tokenization and logprobs differently, the OpenAI-compatible backend is an approximation rather than an exact replacement for local logits.

## How it works

```text
JevRequest
  -> compile candidates into yes/no prompts
  -> backend reads next-token yes/no scores
  -> normalize scores and assemble JevResponse
```

MyJev does not ask the model to generate a JSON object. Instead, each candidate becomes an independent binary judgment. The core then combines those probabilities according to the question type.

With SGLang, candidate submissions are staged so shared `state` and `instructions` prefixes can be reused through the Radix Cache:

![Staged candidate scoring reuses state and question instructions through SGLang Radix Cache.](assets/shared-prefix-stages.svg)

See [From Jev request to LLM request](docs/request-to-model.md) and [Shared-prefix design](docs/shared-prefix-cache.md) for the complete model.

## Backends

| Backend | Best for | Requirements | Shared-prefix staging |
| --- | --- | --- | --- |
| OpenAI-compatible API | Managed APIs and existing model services | First-token top logprobs | Not applicable |
| SGLang | High-throughput local inference | Linux and a supported NVIDIA GPU | Yes |
| Transformers | Local tests, research, CPU/CUDA fallback | `myjev[transformers]` | No |

## Documentation

| Guide | Description |
| --- | --- |
| [Installation](docs/installation.md) | Installation details and backend extras |
| [Usage](docs/usage.md) | Python examples, HTTP service, and submission modes |
| [Request to model](docs/request-to-model.md) | How Jev-style questions become model inputs |
| [Shared-prefix cache](docs/shared-prefix-cache.md) | SGLang candidate staging and cache reuse |
| [Benchmarks](docs/shared-prefix-benchmarks.md) | Shared-prefix staging results |

## Project structure

```text
src/myjev/       Implementation
tests/           Unit and backend tests
examples/        Runnable backend examples
docs/            Installation, usage, design, and benchmark guides
assets/          Diagrams and images
```

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

The tests do not require a model download. Contribution and security policies are documented in [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Credits

- [LLM2Jev](https://github.com/Yinsongxu/LLM2Jev) inspired MyJev's prefill-only candidate scoring approach.
- [Jev confidence documentation](https://docs.typesafe.ai/confidence) is referenced when describing this project's inferred probability assembly.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
