# Candidate scoring in MyJev

[简体中文](request-to-model_zh.md) · [Back to README](../README.md)

MyJev turns a structured decision into several binary judgments. Each candidate
receives an independent yes/no prompt. The backend reads the model's next-token
evidence for `yes` and `no`, and Python code normalizes those scores into the
final answer.

## Request model

A MyJev request has three parts:

```json
{
  "state": "My card was charged twice. Please refund the extra charge.",
  "model": "your-model",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which department should handle this request?",
      "criteria": {
        "shipping": "Delivery",
        "billing": "Charges and billing",
        "returns": "Returns and exchanges"
      }
    }
  }
}
```

`state` is the shared evidence. Each question has an objective and candidates.
The `criteria` names are returned in answers, so stable identifiers are useful.

| Request part | Role |
| --- | --- |
| `state` | Evidence shared by all questions |
| `instructions` | The judgment to make |
| `criteria` | Candidates for a choice or score levels |
| `model` | The model name passed to the backend or HTTP service |

## Why score candidates separately?

An ordinary chat-completion approach asks the model to generate a JSON object
with a choice, probabilities, and a confidence value. That format is convenient,
but the numbers are generated text. Missing fields, invalid JSON, extra
explanatory text, and poorly calibrated self-reported confidence are possible
even when a schema is included in the prompt.

MyJev instead compiles each candidate into a question such as:

```text
Context:
My card was charged twice. Please refund the extra charge.

Question:
Evaluation objective: Which department should handle this request?
Candidate: billing
Does this candidate match the context?
Candidate definition: Charges and billing
```

The system message asks for exactly `yes` or `no`. Other candidates use the same
context and objective, replacing only the candidate name and definition. Runtime
options can change without training a new classification head.

The model still evaluates each prompt, but MyJev does not ask it to decode the
final word. Local backends read the next-token logits directly. The
OpenAI-compatible backend asks the API to expose first-token logprobs and looks
for both labels in that top-logprob window. Providers may tokenize or expose
labels differently, so that backend is an approximation of the local logits path.

## From binary scores to answers

For one candidate, the backend produces a probability:

```text
q = exp(yes_logit) / (exp(yes_logit) + exp(no_logit))
```

MyJev then groups the candidate scores by question:

| Question type | Binary scoring | Final result |
| --- | --- | --- |
| `Choice` | One judgment per option | Normalize scores, return the distribution and highest option |
| `Score` | One judgment per level, starting at 0 | Normalize scores and compute the weighted level average |
| `Noul`, no criteria | Judge the original question | Return the yes score |
| `Noul`, with criteria | Judge `true` and `false` interpretations | Normalize both scores and return the `true` score |

For example, raw choice scores `[0.2, 0.8, 0.2]` normalize to approximately
`[0.167, 0.667, 0.167]`. A score distribution `[0.2, 0.7, 0.1]` yields a final
score of `0.9`. These are arithmetic examples, not measured model outputs.

Ties in `Choice` select the first candidate in the original criteria order.
`Score` levels keep their given order because that order defines the levels.
When all raw scores are zero, MyJev returns a uniform distribution.

## Confidence

For `Choice` and `Score`, confidence describes how concentrated the normalized
distribution is. With `n` candidates and maximum probability `p_max`, MyJev
computes:

```text
confidence = 1, when n = 1
confidence = (n * p_max - 1) / (n - 1), when n > 1
```

The value is clamped to `[0, 1]`. A uniform distribution gives confidence 0; all
probability mass on one candidate gives confidence 1. This is a property of the
produced distribution, not a calibrated probability that the decision is correct.
`Noul` has no separate confidence field.

## Cost and reuse

Separate candidates repeat `state` and question instructions. More candidates,
longer evidence, or longer instructions increase the logical input-token count.
The tradeoff is that the answer distribution itself is not generated token by
token, which removes decode time and JSON parsing risk from this stage.

With SGLang, shared prefixes can be computed once and reused. See
[Shared-prefix submission](shared-prefix-cache.md) for how MyJev stages those
submissions.
