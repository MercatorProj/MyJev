"""Run an approximate MyJev request with an OpenAI-compatible API."""

from __future__ import annotations

import argparse
import os

from myjev import (
    Choice,
    MyJev,
    Noul,
    OpenAICompatibleBackend,
    Score,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an approximate OpenAI-compatible MyJev inference example.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="Model name understood by the API",
    )
    parser.add_argument("--base-url", help="OpenAI-compatible base URL")
    parser.add_argument("--top-logprobs", type=int, default=20)
    parser.add_argument("--system-role", choices=("system", "user"), default="user")
    parser.add_argument("--max-concurrency", type=int, default=1)
    args = parser.parse_args()

    backend = OpenAICompatibleBackend(
        base_url=args.base_url,
        top_logprobs=args.top_logprobs,
        system_role=args.system_role,
        max_concurrency=args.max_concurrency,
    )
    response = MyJev(backend=backend, model=args.model).system_one(
        state="客户说包裹一直没有送到，希望查询物流并尽快处理。",
        questions={
            "is_delivery_issue": Noul(
                instructions="这是否是一个物流配送问题？",
            ),
            "department": Choice(
                instructions="这个请求应该交给哪个部门处理？",
                criteria={
                    "billing": "付款、账单或退款问题",
                    "shipping": "物流、配送或包裹丢失问题",
                    "technical": "产品故障或技术支持问题",
                },
            ),
            "urgency": Score(
                instructions="评估这个客户请求的紧急程度。",
                criteria=["不紧急", "比较紧急", "非常紧急"],
            ),
        },
    )
    print(response.json)


if __name__ == "__main__":
    main()
