import json
import os
import unittest
from unittest.mock import patch

from myjev import OpenAICompatibleBackend


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None


def api_response(yes_logprob: float, no_logprob: float) -> bytes:
    return json.dumps({
        "choices": [{
            "message": {"content": "yes"},
            "logprobs": {
                "content": [{
                    "top_logprobs": [
                        {"token": "yes", "logprob": yes_logprob},
                        {"token": "no", "logprob": no_logprob},
                    ],
                }],
            },
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 1},
    }).encode("utf-8")


class OpenAICompatibleBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompts = (
            ({"role": "user", "content": "first"},),
            ({"role": "user", "content": "second"},),
        )

    def test_normalizes_yes_no_top_logprobs_in_order(self) -> None:
        requests = []

        def fake_urlopen(request: object, timeout: float) -> FakeResponse:
            requests.append(request)
            if len(requests) == 1:
                return FakeResponse(api_response(-0.3566749439, -1.2039728043))
            return FakeResponse(api_response(-2.3025850930, -0.1053605157))

        backend = OpenAICompatibleBackend(api_key="test-key")
        with patch(
            "myjev.backend.openai_compatible_backend._urlopen",
            side_effect=fake_urlopen,
        ):
            output = backend.score(model="test-model", prompts=self.prompts)

        self.assertAlmostEqual(output.yes_probabilities[0], 0.7)
        self.assertAlmostEqual(output.yes_probabilities[1], 0.1)
        self.assertEqual(output.usage.input_tokens, 20)
        self.assertEqual(output.usage.output_tokens, 2)
        self.assertEqual(len(requests), 2)
        for request, prompt in zip(requests, self.prompts):
            self.assertEqual(
                request.get_full_url(),
                "https://api.openai.com/v1/chat/completions",
            )
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            payload = json.loads(request.data)
            self.assertEqual(payload["model"], "test-model")
            self.assertEqual(payload["messages"], [dict(message) for message in prompt])
            self.assertEqual(payload["max_tokens"], 1)
            self.assertTrue(payload["logprobs"])
            self.assertEqual(payload["top_logprobs"], 20)

    def test_preserves_base_url_and_labels(self) -> None:
        request_holder = []

        def fake_urlopen(request: object, timeout: float) -> FakeResponse:
            request_holder.append(request)
            return FakeResponse(api_response(-1.0, -1.0))

        backend = OpenAICompatibleBackend(
            api_key="test-key",
            base_url="http://localhost:8000/v1/",
            top_logprobs=5,
            yes_label="YES",
            no_label="NO",
        )
        with patch(
            "myjev.backend.openai_compatible_backend._urlopen",
            side_effect=fake_urlopen,
        ):
            output = backend.score(model="model", prompts=self.prompts[:1])

        self.assertEqual(output.yes_probabilities, (0.5,))
        payload = json.loads(request_holder[0].data)
        self.assertEqual(
            request_holder[0].get_full_url(),
            "http://localhost:8000/v1/chat/completions",
        )
        self.assertEqual(payload["top_logprobs"], 5)

    def test_rejects_missing_yes_or_no_logprobs(self) -> None:
        body = json.dumps({
            "choices": [{
                "logprobs": {
                    "content": [{"top_logprobs": [{"token": "yes", "logprob": -1.0}]}],
                },
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }).encode("utf-8")

        backend = OpenAICompatibleBackend(api_key="test-key")
        with patch(
            "myjev.backend.openai_compatible_backend._urlopen",
            side_effect=lambda request, timeout: FakeResponse(body),
        ):
            with self.assertRaisesRegex(ValueError, "both yes and no"):
                backend.score(model="model", prompts=self.prompts[:1])

    def test_rejects_invalid_constructor_settings(self) -> None:
        original = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = ""
        try:
            with self.assertRaisesRegex(ValueError, "api_key"):
                OpenAICompatibleBackend()
        finally:
            if original is None:
                del os.environ["OPENAI_API_KEY"]
            else:
                os.environ["OPENAI_API_KEY"] = original

        for kwargs in (
            {"api_key": "key", "top_logprobs": 0},
            {"api_key": "key", "top_logprobs": 21},
            {"api_key": "key", "timeout": 0},
            {"api_key": "key", "max_concurrency": 0},
            {"api_key": "key", "yes_label": "same", "no_label": "same"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                OpenAICompatibleBackend(**kwargs)

    def test_rejects_empty_prompts_before_api_call(self) -> None:
        backend = OpenAICompatibleBackend(api_key="test-key")
        with patch(
            "myjev.backend.openai_compatible_backend._urlopen"
        ) as mock_urlopen:
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                backend.score(model="model", prompts=())
        mock_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
