  <p align="center">
    <img src="assets/myjev-banner.jpeg" alt="MyJev" width="100%">
  </p>

# MyJev

[English](README.md)

[![Tests](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml/badge.svg)](https://github.com/MercatorProj/MyJev/actions/workflows/test.yml)

**MyJev 是一个轻量级 Jev 包装，用于语言模型。** 它把运行时定义的 `Choice`、`Score` 和 `Noul` 问题转换成 prefill-only 的 yes/no 判断，再返回带归一化概率的类型化答案。

本项目受 [LLM2Jev](https://github.com/Yinsongxu/LLM2Jev) 启发，把该思路重新实现为一个围绕现有模型 API 和推理后端的小型 Python 层。MyJev 不训练、微调、托管或修改模型。

MyJev 是独立的开源项目，与 Jev、TypeSafe 或 LLM2Jev 的作者没有隶属关系，也未获得其认可或授权。

## 为什么使用 MyJev

- 请求结构保持紧凑：直接在 `JevRequest` 中表达选项和等级。
- 不依赖自由生成和临时的 JSON 解析来得到结构化决策。
- 只需要 logprob 访问时，可直接使用已有的 OpenAI 兼容 API。
- 需要高吞吐本地推理时，使用 SGLang 并复用共享前缀。

需要 Python 3.10 或更新版本。

## 安装

当前从源码安装：

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

设置模型服务地址和密钥：

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
```

PowerShell 使用：

```powershell
$env:OPENAI_BASE_URL = "https://your-openai-compatible-service/v1"
$env:OPENAI_API_KEY = "your-api-key"
```

然后运行示例：

```bash
python examples/openai_compatible_inference.py --model your-model-name
```

API 必须返回首生成 token 的 top logprobs，并且窗口中同时包含 `yes` 和 `no`。不同服务对分词和 logprobs 的暴露方式可能不同，因此 OpenAI 兼容后端是近似实现，不是本地 logits 的完全等价替代。

## 工作方式

```text
JevRequest
  -> 把候选编译成 yes/no 输入
  -> 后端读取下一个 token 的 yes/no 分数
  -> 归一化分数并组装 JevResponse
```

MyJev 不要求模型生成 JSON 对象。每个候选都会变成一个独立的二元判断，核心层再根据题型把这些概率组合成最终答案。

使用 SGLang 时，候选提交会分阶段进行，让共享的 `state` 和 `instructions` 前缀通过 Radix Cache 复用：

![候选分阶段评分，通过 SGLang Radix Cache 复用 state 和题目的 instructions。](assets/shared-prefix-stages.svg)

完整原理见[从 Jev request 到 LLM request](docs/request-to-model_zh.md)和[共享前缀设计](docs/shared-prefix-cache_zh.md)。

## 后端

| 后端 | 适合场景 | 依赖要求 | 共享前缀分阶段 |
| --- | --- | --- | --- |
| OpenAI 兼容 API | 托管 API 和已有模型服务 | 首 token 的 top logprobs | 不适用 |
| SGLang | 高吞吐本地推理 | Linux 和受支持的 NVIDIA GPU | 支持 |
| Transformers | 本地测试、研究和 CPU/CUDA 回退 | `myjev[transformers]` | 不支持 |

## 文档

| 指南 | 说明 |
| --- | --- |
| [安装](docs/installation_zh.md) | 安装方式和后端依赖 |
| [使用](docs/usage_zh.md) | Python 示例、HTTP 服务和提交模式 |
| [Request 到模型](docs/request-to-model_zh.md) | Jev 风格问题如何变成模型输入 |
| [共享前缀缓存](docs/shared-prefix-cache_zh.md) | SGLang 候选分阶段与缓存复用 |
| [性能测评](docs/shared-prefix-benchmarks_zh.md) | 共享前缀分阶段结果 |

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
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

测试不需要下载模型。贡献和安全政策分别见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

## 致谢

- [LLM2Jev](https://github.com/Yinsongxu/LLM2Jev) 启发了 MyJev 的 prefill-only 候选评分思路。
- 描述本项目的概率组装方式时参考了 [Jev confidence 文档](https://docs.typesafe.ai/confidence)。

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 发布。
