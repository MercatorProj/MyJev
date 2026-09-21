
  <p align="center">
    <img src="assets/myjev-banner.jpeg" alt="MyJev" width="100%">
  </p>

# MyJev: structured decisions from language models

[简体中文](README_zh.md)

MyJev adapts language models to Jev-style structured decisions. It accepts runtime-defined `Choice`, `Score`, and `Noul` questions and returns typed answers with probabilities.

> MyJev is an independent open-source project. It is not affiliated with or endorsed by Jev or TypeSafe.

## Backend support

| Backend | Best for | Requirements | Prefix-cache staging |
| --- | --- | --- | --- |
| OpenAI-compatible | Managed APIs and existing model services | An API that returns first-token top logprobs | Not applicable |
| SGLang | High-throughput local inference on NVIDIA GPUs | Linux, supported NVIDIA GPU, `myjev[sglang]` | Yes |
| Transformers | Local tests, research, and CPU/CUDA fallback | `myjev[transformers]` | No |

The OpenAI-compatible backend does not train, host, or fine-tune models. It calls your existing model API.

## Quick start with a model API

Use this path on Windows, macOS, or Linux:

```bash
git clone https://github.com/MercatorProj/MyJev.git
cd MyJev
uv sync

export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
python examples/openai_compatible_inference.py --model your-model-name
```

On PowerShell, use `$env:OPENAI_BASE_URL` and `$env:OPENAI_API_KEY` instead of `export`.

The API must return the top logprobs for the first generated token and include both `yes` and `no` in that window. `top_logprobs` can be increased up to 20; some providers tokenize or expose logprobs differently, so this backend is best treated as an approximation rather than a drop-in replacement for local logits.

## Quick start with a local model

On Linux with a supported NVIDIA GPU, run a local model through SGLang:

```bash
uv sync --extra sglang
source .venv/bin/activate
python examples/sglang_inference.py --model-path /path/to/model
```

Replace `/path/to/model` with a local Hugging Face-compatible causal language model directory. For a Transformers-only environment, use `uv sync --extra transformers` and `examples/transformers_inference.py`.

## How it works

MyJev converts each candidate into an independent yes/no judgment. Instead of asking the model to generate a JSON answer, a backend reads the next-token scores for `yes` and `no`. Code then normalizes the scores and assembles the response.

All candidates share `state`, and candidates for the same question share `instructions`. With SGLang, MyJev stages candidate submissions so shared prefixes are established once and reused through the Radix Cache.

![Staged candidate scoring reuses state and question instructions through SGLang Radix Cache.](assets/shared-prefix-stages.svg)

Learn more in [From Jev request to LLM request](docs/request-to-model.md) and [Shared-prefix design](docs/shared-prefix-cache.md).

## Usage

The [usage guide](docs/usage.md) covers:

- OpenAI-compatible API backend
- SGLang Python API
- Transformers backend
- System One HTTP API
- Choosing between `staged` and `all`

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
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for workflow details. Security issues should follow [SECURITY.md](SECURITY.md) and should not be opened as public issues.

## Maintainers

MyJev is maintained by [MercatorProj](https://github.com/MercatorProj). See [AUTHORS.md](AUTHORS.md) for contributor information.

## Roadmap

- More benchmarks across model sizes, datasets, and workloads.
- An interactive web demo for submitting questions and inspecting probabilities.
- Multimodal model and input support.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
