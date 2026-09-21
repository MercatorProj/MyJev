# Usage

[简体中文](usage_zh.md) · [Back to README](../README.md)

MyJev supports OpenAI-compatible APIs and local SGLang or Transformers models.
For local examples, replace `/path/to/model` with a Hugging Face-compatible
causal language model directory.

## OpenAI-compatible API

Set the connection in your environment:

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
```

On PowerShell, use `$env:OPENAI_BASE_URL` and `$env:OPENAI_API_KEY`.

Use the `request` shown in the SGLang example below.

```python
import os
from myjev import MyJev, OpenAICompatibleBackend

backend = OpenAICompatibleBackend(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    top_logprobs=20,
    system_role="user",
    max_concurrency=2,
)
response = MyJev(backend=backend).evaluate(request)
print(response.to_dict())
```

The first generated token must expose both `yes` and `no` in its top-logprob
window. `top_logprobs` accepts values from 1 to 20. `max_concurrency` controls
how many candidate judgments are sent concurrently.

Run the bundled example:

```bash
python examples/openai_compatible_inference.py --model your-model-name --top-logprobs 20
```

## SGLang Python API

This example uses `Choice`, `Score`, and `Noul`. The local SGLang backend
defaults to staged candidate submission:

```python
from myjev import Choice, JevRequest, MyJev, Noul, Score, SGLangBackend

if __name__ == "__main__":
    model_path = "/path/to/model"
    request = JevRequest(
        model=model_path,
        state="My parcel arrived two weeks late, and my card was charged twice.",
        questions={
            "department": Choice(
                instructions="Which department should handle this request?",
                criteria={
                    "shipping": "Delivery problems",
                    "billing": "Charges and billing problems",
                    "returns": "Returns and exchanges",
                },
            ),
            "severity": Score(
                instructions="How severe is the problem?",
                criteria=["Low: minor impact", "Medium: impaired but usable", "High: unusable"],
            ),
            "delivery": Noul(
                instructions="Is this a delivery issue?",
            ),
        },
    )
    with SGLangBackend(model_path, submission="staged") as backend:
        response = MyJev(backend=backend).evaluate(request)
        print(response.to_dict())
```

Keep the main guard because SGLang starts worker processes. Reuse the backend for
multiple requests inside the same `with` block. `engine_kwargs` passes options to
the SGLang engine.

To submit all candidates together:

```python
with SGLangBackend(model_path, submission="all") as backend:
    response = MyJev(backend=backend).evaluate(request)
```

Run the bundled example with either mode:

```bash
python examples/sglang_inference.py --model-path /path/to/model --submission staged
python examples/sglang_inference.py --model-path /path/to/model --submission all
```

## Transformers backend

In a Transformers-only environment:

```bash
python examples/transformers_inference.py --model-path /path/to/model
```

```python
from myjev import MyJev, TransformersBackend

backend = TransformersBackend(model_path)
response = MyJev(backend=backend).evaluate(request)
print(response.to_dict())
```

The backend uses CUDA when available and falls back to CPU otherwise.

## MyJev HTTP API

`myjev-serve` adds `POST /v1/myjev` to SGLang's HTTP server. Model listing,
health checks, authentication, and SGLang's native endpoints remain unchanged.

```bash
export MYJEV_API_KEY="replace-with-your-api-key"
myjev-serve \
  --model-path /path/to/model \
  --served-model-name local-model \
  --host 0.0.0.0 \
  --port 30000 \
  --api-key "$MYJEV_API_KEY"
```

Check the native model endpoint:

```bash
curl http://localhost:30000/v1/models \
  -H "Authorization: Bearer $MYJEV_API_KEY"
```

Submit a MyJev request:

```bash
curl http://localhost:30000/v1/myjev \
  -H "Authorization: Bearer $MYJEV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "The customer package has not arrived.",
    "model": "local-model",
    "questions": {
      "delivery": {
        "type": "noul",
        "instructions": "Is this a delivery issue?"
      }
    }
  }'
```

Use `--submission staged|all` to select candidate submission for `/v1/myjev`.
The default is `staged`; `staged` requires Radix Cache, while `all` can be used
with `--disable-radix-cache`. The setting applies to the whole server process.

The command also accepts SGLang's normal server arguments. It currently requires
the default single-tokenizer HTTP mode and does not support
`--skip-tokenizer-init`.

## Choosing a mode

| Request pattern | Starting point | Reason |
| --- | --- | --- |
| Long context, many candidates, no relevant cached prefix | `staged` (default) | Avoids repeated processing within a cold request |
| Short input, few candidates | `all` | Submission rounds may cost more than they save |
| Repeated requests with mostly cached prefixes | `all` | Existing cache can be reused directly |
| Partial cache hits or highly varied inputs | Compare both | The benefit depends on shared computation and submission overhead |

MyJev does not detect cache state and switch automatically. Having a shared
prefix does not guarantee that extra rounds will be faster.

See [Performance benchmarks](shared-prefix-benchmarks.md) for measurements and
[Shared-prefix submission](shared-prefix-cache.md) for reuse behavior.
