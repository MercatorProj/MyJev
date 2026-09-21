# MyJev

[简体中文](README_zh.md)

[![Tests](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml/badge.svg)](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml)

MyJev is a lightweight Python library for structured decision scoring. It accepts
runtime-defined `Choice`, `Score`, and `Noul` questions, turns each candidate
into a binary yes/no scoring task, and returns typed answers with normalized
probabilities.

The package is a thin orchestration layer around existing model APIs and
inference runtimes. It does not train, fine-tune, host, or modify models.

## Primitives

| Primitive | Use it for | Answer |
| --- | --- | --- |
| `Choice` | Mutually exclusive options | The highest option, its confidence, and the full probability distribution |
| `Score` | One ordered scale | A probability-weighted score, its confidence, and the level distribution |
| `Noul` | An independent yes/no condition | The probability that the condition is true |

## Install

Python 3.10 or newer is required.

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

Point MyJev at an OpenAI-compatible chat endpoint:

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
python examples/openai_compatible_inference.py --model your-model-name
```

On PowerShell:

```powershell
$env:OPENAI_BASE_URL = "https://your-openai-compatible-service/v1"
$env:OPENAI_API_KEY = "your-api-key"
```

The API must expose first-token top logprobs containing both `yes` and `no`.
Providers differ in tokenization and logprob exposure, so this backend is
approximate rather than an exact substitute for local logits.

## Example

```python
from myjev import Choice, JevRequest, MyJev, Noul, OpenAICompatibleBackend
from myjev import Score

backend = OpenAICompatibleBackend(
    base_url="https://your-openai-compatible-service/v1",
    api_key="your-api-key",
    top_logprobs=20,
)
request = JevRequest(
    model="your-model-name",
    state="The customer says a card was charged twice and asks for a refund.",
    questions={
        "department": Choice(
            instructions="Which department should handle this request?",
            criteria={
                "billing": "Charges and billing",
                "returns": "Returns and exchanges",
            },
        ),
        "severity": Score(
            instructions="How severe is the issue?",
            criteria=["Minor", "Disruptive", "Blocking"],
        ),
        "refund": Noul(instructions="Is the customer asking for a refund?"),
    },
)

response = MyJev(backend=backend).evaluate(request)
print(response.json)
```

An illustrative response is:

```json
{
  "model": "your-model-name",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "billing",
      "confidence": 0.58,
      "probabilities": {
        "billing": 0.72,
        "returns": 0.21,
        "shipping": 0.07
      }
    },
    "severity": {
      "type": "score",
      "score": 1.15,
      "confidence": 0.48,
      "legend": {
        "0": "Minor",
        "1": "Disruptive",
        "2": "Blocking"
      },
      "probabilities": {
        "0": 0.10,
        "1": 0.65,
        "2": 0.25
      }
    },
    "refund": {
      "type": "noul",
      "noul": 0.92
    }
  },
  "usage": {
    "input_tokens": 74,
    "output_tokens": 0
  }
}
```

The probabilities are model-derived scores; the values above are only an example.

## How it works

```text
structured request
  -> compile each candidate into a yes/no prompt
  -> score the next token for yes/no
  -> normalize scores and assemble a typed response
```

This avoids free-form generation and JSON parsing for the structured answer
itself. The OpenAI-compatible backend uses chat-completion logprobs. SGLang and
Transformers can score local models directly from logits.

With SGLang, MyJev can stage candidate submissions so shared `state` and
`instructions` prefixes are reused through the Radix Cache.

## Backends

| Backend | Best for | Requirements | Shared-prefix staging |
| --- | --- | --- | --- |
| OpenAI-compatible API | Existing managed APIs | First-token top logprobs | Not applicable |
| SGLang | High-throughput local inference | Linux, supported NVIDIA GPU | Yes |
| Transformers | Local tests and research | `myjev[transformers]` | No |

The optional `myjev-serve` command adds `POST /v1/myjev` to an SGLang HTTP
server.

## Documentation

- [Installation](docs/installation.md)
- [Usage](docs/usage.md)
- [Candidate scoring](docs/request-to-model.md)
- [Shared-prefix submission](docs/shared-prefix-cache.md)
- [Benchmarks](docs/shared-prefix-benchmarks.md)

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Tests use mocks and do not download models.

## License

Apache License 2.0. See [LICENSE](LICENSE).
