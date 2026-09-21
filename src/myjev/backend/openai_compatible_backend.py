from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Sequence
from typing import Any, Literal

from ..core.response import Usage
from ..inference.prompt import ChatPrompt
from .base import BinaryBackendOutput


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TOP_LOGPROBS = 20


class OpenAICompatibleBackend:
    """Approximate binary scorer using an OpenAI-compatible chat API.

    The API generates one token and returns token logprobs.  Unlike the
    local backends, this depends on the provider returning both yes/no
    candidates inside the selected top-logprob window.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        top_logprobs: int = DEFAULT_TOP_LOGPROBS,
        yes_label: str = "yes",
        no_label: str = "no",
        system_role: Literal["system", "user"] = "user",
        timeout: float = 60.0,
        max_concurrency: int = 1,
    ) -> None:
        if not isinstance(yes_label, str) or not yes_label:
            raise ValueError("yes_label must be a non-empty string")
        if not isinstance(no_label, str) or not no_label:
            raise ValueError("no_label must be a non-empty string")
        if yes_label.lower() == no_label.lower():
            raise ValueError("yes_label and no_label must differ")
        if (
            isinstance(top_logprobs, bool)
            or not isinstance(top_logprobs, int)
            or not 1 <= top_logprobs <= 20
        ):
            raise ValueError("top_logprobs must be an integer from 1 to 20")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if (
            isinstance(max_concurrency, bool)
            or not isinstance(max_concurrency, int)
            or max_concurrency < 1
        ):
            raise ValueError("max_concurrency must be an integer of at least 1")
        if system_role not in {"system", "user"}:
            raise ValueError("system_role must be 'system' or 'user'")

        selected_base_url = base_url or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL
        if not isinstance(selected_base_url, str) or not selected_base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        selected_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not isinstance(selected_api_key, str) or not selected_api_key:
            raise ValueError("api_key must be provided or OPENAI_API_KEY must be set")

        self.base_url = selected_base_url.rstrip("/")
        self.api_key = selected_api_key
        self.top_logprobs = top_logprobs
        self.yes_label = yes_label
        self.no_label = no_label
        self.system_role = system_role
        self.timeout = timeout
        self.max_concurrency = max_concurrency

    def score(
        self,
        *,
        model: str,
        prompts: Sequence[ChatPrompt],
    ) -> BinaryBackendOutput:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        prompt_values = tuple(prompts)
        if not prompt_values:
            raise ValueError("prompts must not be empty")

        if self.max_concurrency == 1:
            responses = [self._score_prompt(model, prompt) for prompt in prompt_values]
        else:
            with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
                responses = list(
                    executor.map(
                        lambda prompt: self._score_prompt(model, prompt),
                        prompt_values,
                    )
                )

        probabilities = tuple(response[0] for response in responses)
        input_tokens = sum(response[1] for response in responses)
        output_tokens = sum(response[2] for response in responses)
        return BinaryBackendOutput(
            yes_probabilities=probabilities,
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
        )

    def _score_prompt(self, model: str, prompt: ChatPrompt) -> tuple[float, int, int]:
        payload = {
            "model": model,
            "messages": _messages_for_api(prompt, system_role=self.system_role),
            "max_tokens": 1,
            "temperature": 0,
            "logprobs": True,
            "top_logprobs": self.top_logprobs,
            "n": 1,
            "stream": False,
        }
        data = self._post(payload)
        probability = _yes_probability(
            data,
            yes_label=self.yes_label,
            no_label=self.no_label,
        )
        usage = data.get("usage") or {}
        return (
            probability,
            _nonnegative_int(usage.get("prompt_tokens"), "prompt_tokens"),
            _nonnegative_int(usage.get("completion_tokens"), "completion_tokens"),
        )

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with _urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenAI-compatible API returned HTTP {error.code}: {body}"
            ) from error

        if not isinstance(result, dict):
            raise ValueError("OpenAI-compatible API response must be a JSON object")
        return result


def _yes_probability(
    data: dict[str, Any],
    *,
    yes_label: str,
    no_label: str,
) -> float:
    try:
        choices = data["choices"]
        logprobs = choices[0]["logprobs"]["content"]
        top_logprobs = logprobs[0]["top_logprobs"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(
            "OpenAI-compatible API did not return first-token top logprobs"
        ) from error

    yes_logprob: float | None = None
    no_logprob: float | None = None
    for entry in top_logprobs:
        try:
            token = str(entry["token"]).strip().lower()
            logprob = float(entry["logprob"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid top-logprob entry returned by the API") from error
        if not math.isfinite(logprob):
            raise ValueError("top-logprob values must be finite")
        if token == yes_label.lower() and yes_logprob is None:
            yes_logprob = logprob
        elif token == no_label.lower() and no_logprob is None:
            no_logprob = logprob

    if yes_logprob is None or no_logprob is None:
        raise ValueError(
            "top logprobs do not contain both yes and no; "
            "increase top_logprobs or use an API with a larger logprob window"
        )
    return math.exp(yes_logprob) / (math.exp(yes_logprob) + math.exp(no_logprob))


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"API usage field {field} must be a non-negative integer")
    return value


def _messages_for_api(
    prompt: ChatPrompt,
    *,
    system_role: Literal["system", "user"],
) -> list[dict[str, str]]:
    messages = [dict(message) for message in prompt]
    if system_role == "system":
        return messages

    system_messages = [message for message in messages if message["role"] == "system"]
    user_messages = [message for message in messages if message["role"] != "system"]
    if not system_messages:
        return user_messages

    system_text = "\n\n".join(message["content"] for message in system_messages)
    user_text = "\n\n".join(message["content"] for message in user_messages)
    if not user_text:
        return [{"role": "user", "content": system_text}]
    return [{"role": "user", "content": f"{system_text}\n\n{user_text}"}]


def _urlopen(*args: Any, **kwargs: Any) -> Any:
    return urllib.request.urlopen(*args, **kwargs)
