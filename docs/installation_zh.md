# 安装指南

[English](installation.md) · [返回 README](../README_zh.md)

克隆仓库：

```bash
git clone https://github.com/MercatorProj/MyJev.git
cd MyJev
```

需要 Python 3.10 或更新版本。

## OpenAI 兼容 API

默认安装即可使用 OpenAI 兼容后端：

```bash
uv sync
```

运行示例前设置 API 连接：

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-service/v1"
export OPENAI_API_KEY="your-api-key"
```

PowerShell 中请改用 `$env:OPENAI_BASE_URL` 和 `$env:OPENAI_API_KEY`。

## Transformers 后端

本地 Transformers 后端使用：

```bash
uv sync --extra transformers
```

pip 安装方式：

```bash
python -m pip install -e ".[transformers]"
```

## SGLang 后端

SGLang 面向配有受支持 NVIDIA GPU 的 Linux 环境：

```bash
uv sync --extra sglang
source .venv/bin/activate
```

pip 安装方式：

```bash
python -m pip install -e ".[sglang]"
```

安装完成后，参阅[使用指南](usage_zh.md)运行 Python 示例或启动 HTTP 服务。
