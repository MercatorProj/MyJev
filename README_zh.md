
  <p align="center">
    <img src="assets/myjev-banner.jpeg" alt="MyJev" width="100%">
  </p>

# MyJev：用语言模型生成结构化决策

[English](README.md)

MyJev 将语言模型适配为 Jev 风格的结构化决策模型。它接受运行时定义的 `Choice`、`Score` 和 `Noul` 问题，并返回包含概率的类型化答案。

> MyJev 是一个独立的开源项目，与 Jev 或 TypeSafe 没有关联，也未获得其认可或授权。

## 后端支持

| 后端 | 适合场景 | 依赖要求 | 前缀缓存分阶段 |
| --- | --- | --- | --- |
| OpenAI 兼容 API | 托管 API 和已有模型服务 | API 需返回首 token 的 top logprobs | 不适用 |
| SGLang | NVIDIA GPU 上的高吞吐本地推理 | Linux、受支持的 NVIDIA GPU、`myjev[sglang]` | 支持 |
| Transformers | 本地测试、研究和 CPU/CUDA 回退 | `myjev[transformers]` | 暂不支持 |

OpenAI 兼容后端不训练、部署或微调模型，只调用你已有的模型 API。

## API-only 快速开始

Windows、macOS 和 Linux 都可以先使用这条路径：

```bash
git clone https://github.com/MercatorProj/MyJev.git
cd MyJev
uv sync

export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
python examples/openai_compatible_inference.py --model your-model-name
```

PowerShell 中请改用 `$env:OPENAI_BASE_URL` 和 `$env:OPENAI_API_KEY`。

API 必须返回首生成 token 的 top logprobs，并且结果中同时包含 `yes` 和 `no`。`top_logprobs` 最多可以调到 20；不同服务可能采用不同的分词或日志概率暴露方式，因此应把这个后端视为近似实现，而不是本地 logits 的完全等价替代。

## 本地模型快速开始

在配有受支持 NVIDIA GPU 的 Linux 环境中，使用 SGLang 运行本地模型：

```bash
uv sync --extra sglang
source .venv/bin/activate
python examples/sglang_inference.py --model-path /path/to/model
```

请将 `/path/to/model` 替换为本地 Hugging Face 兼容的因果语言模型目录。若只需 Transformers 后端，使用 `uv sync --extra transformers` 和 `examples/transformers_inference.py`。

## 工作原理

MyJev 会把每个候选转换成独立的 yes/no 判断。模型不需要逐 token 生成 JSON 回答，后端直接读取下一个 token 中 `yes` 和 `no` 的分数，再由代码归一化并组装响应。

所有候选共享 `state`，同一道题的候选还共享 `instructions`。使用 SGLang 时，MyJev 会分阶段提交候选，让公共前缀先建立缓存，再通过 Radix Cache 复用。

![候选分阶段评分，通过 SGLang Radix Cache 复用 state 和题目的 instructions。](assets/shared-prefix-stages.svg)

详细原理见[从 Jev Request 到 LLM Request](docs/request-to-model_zh.md)和[共享前缀设计](docs/shared-prefix-cache_zh.md)。

## 使用

[使用指南](docs/usage_zh.md)覆盖以下内容：

- OpenAI 兼容 API 后端
- SGLang Python API
- Transformers 后端
- System One HTTP API
- `staged` 与 `all` 的选择

## 项目结构

```text
src/myjev/       实现
tests/           单元测试和后端测试
examples/        可运行的后端示例
docs/            安装、使用、设计和性能测评文档
assets/          图示和图片
```

## 开发

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

提交流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请遵循 [SECURITY.md](SECURITY.md)，不要在公开 issue 中提交。

## 维护者

MyJev 由 [MercatorProj](https://github.com/MercatorProj) 维护。贡献者信息见 [AUTHORS.md](AUTHORS.md)。

## Roadmap

- 更多 benchmark：覆盖不同模型规模、数据集和工作负载。
- 网页 demo：交互式提交问题并查看概率结果。
- 支持多模态模型与输入。

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 发布。
