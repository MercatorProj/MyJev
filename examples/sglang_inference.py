"""Evaluate a structured request with a local SGLang engine."""

import argparse

from myjev import Choice, MyJev, Noul, Score, SGLangBackend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--submission", choices=["all", "staged"], default="staged")
    args = parser.parse_args()
    questions = {
        "delivery": Noul(instructions="这是否是一个物流配送问题？"),
        "department": Choice(
            instructions="哪个部门应该处理这个请求？",
            criteria={"shipping": "物流配送", "billing": "付款账单", "technical": "产品故障"},
        ),
        "urgency": Score(
            instructions="这个请求有多紧急？", criteria=["不紧急", "比较紧急", "非常紧急"],
        ),
    }
    options = {"mem_fraction_static": 0.4, "disable_cuda_graph": True, "attention_backend": "triton"}
    with SGLangBackend(args.model_path, submission=args.submission, engine_kwargs=options) as backend:
        response = MyJev(backend=backend, model=args.model_path).system_one(
            state="客户说包裹一直没有送到，希望查询物流并尽快处理。",
            questions=questions,
        )
        print(response.json)


if __name__ == "__main__":
    main()
