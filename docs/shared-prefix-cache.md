# Shared-prefix submission

[简体中文](shared-prefix-cache_zh.md) · [Back to README](../README.md)

Read [Candidate scoring in MyJev](request-to-model.md) first for the request
model and how binary scores become final answers.

Shared-prefix submission is an SGLang optimization for a single MyJev request
that produces several candidate judgments. It reuses KV results for identical
input prefixes instead of recomputing them. Long inputs with many candidates can
benefit even when no earlier request has populated the cache.

The Python `SGLangBackend` and the `/v1/systemone` endpoint served by `myjev-serve`
default to staged submission. `TransformersBackend` does not currently use this
strategy.

## Why inputs repeat work

Suppose `state` is a customer message, and the request asks which department
should handle it and how severe it is. MyJev turns each choice option and each
score level into a separate yes/no judgment. Their tokenized prompts share this
conceptual structure:

```text
state: customer message
├── department instructions
│   ├── shipping
│   ├── billing
│   └── returns
└── severity instructions
    ├── low
    ├── medium
    └── high
```

All candidates share `state`. Candidates for the same question also share its
`instructions`. The exact reuse boundary is determined after prompt rendering,
chat templating, and tokenization; semantically similar text in a different
position does not guarantee reuse.

As the model processes tokens, it stores attention intermediates in a KV cache.
If a later input has exactly the same token prefix, the engine can reuse those
intermediates and start fresh computation where the input diverges.

## Staged submission

Submitting every candidate at once does not guarantee that a shared prefix has
been computed before those candidates start. Staged submission therefore first
sends a real candidate to establish the prefix, then sends candidates that can
reuse it. Independent branches can run in the same stage; deeper branches may
need another stage.

![Six criteria candidates scored in stages, reusing state and question instructions through SGLang Radix Cache.](../assets/shared-prefix-stages.svg)

For the example above, a possible sequence is:

1. Score one department candidate to establish the shared `state` and department
   instructions.
2. Score the remaining department candidates and one severity candidate. The
   severity candidate establishes its question's prefix.
3. Score the remaining severity candidates.

Each candidate is scored once. There is no extra warm-up question, input content
is unchanged, and answers return in their original question and candidate order.
Actual grouping follows token prefixes and is not fixed to three stages.

Here, a **cold request** has no relevant cached prefix even though the model is
loaded and kernels are warm. Staging establishes and reuses cache within that
same request. It does not accelerate model loading or kernel compilation.

## Outputs and limits

Submission mode does not change response structures. MyJev still reads next-token
yes/no scores without generating answer text. `usage.input_tokens` counts the
logical total across complete candidate inputs; `usage.output_tokens` is zero.
Cache hits reduce computation, not that logical count.

BF16 results can vary slightly with execution order and batch shape. Candidates
with close scores may change rank when comparing modes. Compare assembled and
normalized answers when evaluating behavior.

Staged submission requires SGLang's Radix Cache. Combining it with
`engine_kwargs={"disable_radix_cache": True}` or `--disable-radix-cache` raises
an error. SGLang controls allocation, reuse, and eviction; prefixes may survive
across requests or be evicted when space is needed. Reuse does not necessarily
reduce displayed GPU memory usage because the engine may preallocate a KV pool.

Serialize calls to a Python backend instance. Concurrent performance of staged
submission in the HTTP service has not yet been validated.
