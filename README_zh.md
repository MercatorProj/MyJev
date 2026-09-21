# MyJev

[English](README.md)

[![Tests](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml/badge.svg)](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml)

MyJev 是一个轻量级 Python 库，用于结构化决策评分。它接受运行时定义的
`Choice`、`Score` 和 `Noul` 问题，把每个候选转换成二元 yes/no 评分任务，并返回
带归一化概率的类型化答案。

本项目只负责围绕现有模型 API 和推理后端编排请求，不训练、微调、托管或修改
模型。

## 元语

| 元语 | 适用场景 | 返回内容 |
| --- | --- | --- |
| `Choice` | 一组互斥选项 | 最高概率选项、置信度和完整概率分布 |
| `Score` | 一条有序量表 | 概率加权分数、置信度和档位分布 |
| `Noul` | 一个独立的 yes/no 判断 | 条件成立的概率 |

## 安装

需要 Python 3.10 或更新版本。

```bash
git clone https://github.com/MercatorProj/MyJev.git
cd MyJev
python -m pip install -e .
```

可选后端依赖：

```bash
python -m pip install -e ".[transformers]"
python -m pip install -e ".[sglang]"
```

`sglang` 适用于配有受支持 NVIDIA GPU 的 Linux 环境。

## 模型 API 快速开始

把 MyJev 指向一个 OpenAI 兼容 chat endpoint：

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
python examples/openai_compatible_inference.py --model your-model-name
```

PowerShell：

```powershell
$env:OPENAI_BASE_URL = "https://your-openai-compatible-service/v1"
$env:OPENAI_API_KEY = "your-api-key"
```

API 必须暴露首生成 token 的 top logprobs，并且窗口中同时包含 `yes` 和 `no`。
不同服务的分词和 logprobs 暴露方式不同，因此这个后端是近似实现，不是本地
logits 的完全等价替代。

## 示例

```python
from myjev import Choice, MyJev, Noul, OpenAICompatibleBackend, Score

backend = OpenAICompatibleBackend(
    base_url="https://your-openai-compatible-service/v1",
    api_key="your-api-key",
    top_logprobs=20,
)
response = MyJev(backend=backend, model="your-model-name").system_one(
    state="客户说信用卡被重复扣款，并要求退款。",
    questions={
        "department": Choice(
            instructions="哪个部门应该处理这个请求？",
            criteria={
                "billing": "扣款和账单",
                "returns": "退货和换货",
            },
        ),
        "severity": Score(
            instructions="这个问题有多严重？",
            criteria=["轻微", "影响使用", "无法使用"],
        ),
        "refund": Noul(instructions="客户是否要求退款？"),
    },
)
print(response.json)
```

输出结构示例如下：

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
        "returns": 0.28
      }
    },
    "severity": {
      "type": "score",
      "score": 1.15,
      "confidence": 0.48,
      "legend": {
        "0": "轻微",
        "1": "影响使用",
        "2": "无法使用"
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

概率来自模型的候选评分，上面的数值只是示例。

## 工作方式

```text
结构化请求
  -> 把每个候选编译成 yes/no 提示
  -> 对下一个 token 中的 yes/no 评分
  -> 归一化分数并组装类型化响应
```

结构化答案本身不依赖自由生成和 JSON 解析。OpenAI 兼容后端使用 chat-completion
logprobs；SGLang 和 Transformers 可以直接从本地模型的 logits 评分。

使用 SGLang 时，MyJev 可以分阶段提交候选，让共享的 `state` 和 `instructions`
前缀通过 Radix Cache 复用。

## 后端

| 后端 | 适合场景 | 依赖要求 | 共享前缀分阶段 |
| --- | --- | --- | --- |
| OpenAI 兼容 API | 已有托管 API | 首 token 的 top logprobs | 不适用 |
| SGLang | 高吞吐本地推理 | Linux，受支持的 NVIDIA GPU | 支持 |
| Transformers | 本地测试和研究 | `myjev[transformers]` | 不支持 |

可选的 `myjev-serve` 命令会在 SGLang HTTP 服务上增加 `POST /v1/systemone`。

## 文档

- [安装](docs/installation_zh.md)
- [使用](docs/usage_zh.md)
- [候选评分](docs/request-to-model_zh.md)
- [共享前缀提交](docs/shared-prefix-cache_zh.md)
- [性能测评](docs/shared-prefix-benchmarks_zh.md)

## 开发

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

测试使用 mock，不会下载模型。

## 许可证

Apache License 2.0，详见 [LICENSE](LICENSE)。
