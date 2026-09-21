# 使用指南

[English](usage.md) · [返回 README](../README_zh.md)

MyJev 支持 OpenAI 兼容 API，以及本地 SGLang 或 Transformers 模型。本地示例中的
`/path/to/model` 请替换为 Hugging Face 兼容的因果语言模型目录。

## OpenAI 兼容 API

先设置连接信息：

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
```

PowerShell 使用 `$env:OPENAI_BASE_URL` 和 `$env:OPENAI_API_KEY`。

```python
import os
from myjev import Choice, MyJev, Noul, OpenAICompatibleBackend, Score

backend = OpenAICompatibleBackend(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    top_logprobs=20,
    system_role="user",
    max_concurrency=2,
)

response = MyJev(backend=backend, model="your-model-name").system_one(
    "包裹晚到了两周，信用卡还被扣了两次。",
    questions={
        "department": Choice(
            instructions="哪个部门应该处理这个请求？",
            criteria={
                "shipping": "物流配送问题",
                "billing": "扣款和账单问题",
                "returns": "退货和换货问题",
            },
        ),
        "severity": Score(
            instructions="这个问题有多严重？",
            criteria=["低", "中", "高"],
        ),
        "delivery": Noul(instructions="这是物流配送问题吗？"),
    },
)
print(response.to_dict())
```

首生成 token 的 top-logprob 窗口必须同时包含 `yes` 和 `no`。`top_logprobs`
接受 1 到 20。`max_concurrency` 控制并发提交的候选判断数量。

运行仓库示例：

```bash
python examples/openai_compatible_inference.py --model your-model-name --top-logprobs 20
```

## SGLang Python API

本地 SGLang 后端默认使用分阶段提交：

```python
from myjev import Choice, MyJev, Noul, Score, SGLangBackend

if __name__ == "__main__":
    model_path = "/path/to/model"
    state = "包裹晚到了两周，信用卡还被扣了两次。"
    questions = {
        "department": Choice(
            instructions="哪个部门应该处理这个请求？",
            criteria={
                "shipping": "物流配送问题",
                "billing": "扣款和账单问题",
                "returns": "退货和换货问题",
            },
        ),
        "severity": Score(
            instructions="这个问题有多严重？",
            criteria=["低：影响轻微", "中：存在问题但仍可继续使用", "高：无法继续使用"],
        ),
        "delivery": Noul(instructions="这是物流配送问题吗？"),
    }

    with SGLangBackend(model_path, submission="staged") as backend:
        response = MyJev(backend=backend, model=model_path).system_one(state, questions)
        print(response.to_dict())
```

SGLang 会创建工作进程，因此脚本入口需要 `if __name__ == "__main__":`。批量处理
多个请求时，请在同一个 `with` 块中复用后端。`engine_kwargs` 用于传入 SGLang
引擎配置。

一次提交所有候选时改用：

```python
with SGLangBackend(model_path, submission="all") as backend:
    response = MyJev(backend=backend, model=model_path).system_one(state, questions)
```

仓库示例支持两种模式：

```bash
python examples/sglang_inference.py --model-path /path/to/model --submission staged
python examples/sglang_inference.py --model-path /path/to/model --submission all
```

## Transformers 后端

在仅安装 Transformers 后端依赖的环境中运行：

```bash
python examples/transformers_inference.py --model-path /path/to/model
```

```python
from myjev import MyJev, TransformersBackend

backend = TransformersBackend(model_path)
response = MyJev(backend=backend, model=model_path).system_one(state, questions)
print(response.to_dict())
```

该后端优先使用 CUDA；没有可用 GPU 时回退到 CPU。

## HTTP API

`myjev-serve` 在 SGLang HTTP 服务上增加官方风格的 `POST /v1/systemone`。模型
列表、健康检查、鉴权和 SGLang 原生接口保持不变。

```bash
export MYJEV_API_KEY="replace-with-your-api-key"
myjev-serve \
  --model-path /path/to/model \
  --served-model-name local-model \
  --host 0.0.0.0 \
  --port 30000 \
  --api-key "$MYJEV_API_KEY"
```

查看原生模型列表：

```bash
curl http://localhost:30000/v1/models \
  -H "Authorization: Bearer $MYJEV_API_KEY"
```

提交请求：

```bash
curl http://localhost:30000/v1/systemone \
  -H "Authorization: Bearer $MYJEV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "客户的包裹一直没有送到。",
    "model": "local-model",
    "questions": {
      "delivery": {
        "type": "noul",
        "instructions": "这是物流配送问题吗？"
      }
    }
  }'
```

响应包含 `model`、`answers` 和 `usage`。typed 问题对象会在本地校验；raw 字典
保留原始字段，本地推理会校验三种受支持的元语。

通过 `--submission staged|all` 选择候选提交方式，默认 `staged`。`staged` 依赖
Radix Cache；`all` 可以配合 `--disable-radix-cache` 使用。该设置对整个服务进程
生效。

服务也复用 SGLang 的启动参数，目前要求默认的单 tokenizer HTTP 模式，且不能启用
`--skip-tokenizer-init`。

## 模式选择

| 请求特点 | 建议起点 | 原因 |
| --- | --- | --- |
| 上下文长、候选多，相关缓存尚不存在 | `staged`（默认） | 避免冷请求内部重复处理长前缀 |
| 输入短、候选少 | `all` | 多轮提交开销可能超过收益 |
| 重复请求，大部分前缀已命中缓存 | `all` | 可直接复用已有缓存 |
| 部分命中或输入差异很大 | 对比两种方式 | 是否更快取决于共享量和提交成本 |

MyJev 不会探测缓存状态后自动切换模式。有共享前缀也不代表分轮一定更快。

实测数据见[性能测评](shared-prefix-benchmarks_zh.md)，复用行为见
[共享前缀提交](shared-prefix-cache_zh.md)。
