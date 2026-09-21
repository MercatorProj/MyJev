# MyJev 的候选评分方式

[English](request-to-model.md) · [返回 README](../README_zh.md)

MyJev 把一个结构化决策拆成多个二元判断。每个候选都会得到一个独立的 yes/no
提示；后端读取模型对下一个 token 中 `yes` 和 `no` 的证据，再由 Python 代码把
这些分数归一化并组装成最终答案。

## 请求模型

一次 MyJev 请求包含三部分：

```json
{
  "state": "信用卡重复扣款，请退回多扣的钱。",
  "model": "your-model",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "哪个部门应该处理这个请求？",
      "criteria": {
        "shipping": "物流配送",
        "billing": "扣款和账单",
        "returns": "退货和换货"
      }
    }
  }
}
```

`state` 是所有问题共享的材料。每道题包含判断目标和候选；`criteria` 的键会
出现在最终答案里，因此适合使用稳定标识符。

| 请求部分 | 作用 |
| --- | --- |
| `state` | 所有判断共享的材料 |
| `instructions` | 要做出的判断 |
| `criteria` | Choice 的候选，或 Score 的等级 |
| `model` | 传给后端或 HTTP 服务的模型名称 |

## 为什么要分别评分候选？

普通聊天生成方式通常让模型直接输出一个 JSON 对象，其中包含选择、概率和
confidence。这个格式很直观，但这些数字仍然是模型生成的文本。即使提示词里
给了 JSON Schema，也可能出现字段缺失、非法 JSON、额外解释文字，或
confidence 未经过校准等问题。

MyJev 会把每个候选编译成类似下面的判断：

```text
Context:
信用卡重复扣款，请退回多扣的钱。

Question:
Evaluation objective: 哪个部门应该处理这个请求？
Candidate: billing
Does this candidate match the context?
Candidate definition: 扣款和账单
```

system 消息要求模型只回答 `yes` 或 `no`。其他候选使用相同的材料和判断目标，
只替换候选名称与定义。因此，运行时新增或调整选项不需要训练新的分类头。

模型仍然需要处理这些提示，但 MyJev 不会让它继续生成最后的词。本地后端直接
读取下一个 token 的 logits；OpenAI 兼容后端则请求 API 暴露首生成 token 的
top logprobs，并检查其中是否同时包含两个标签。不同服务的分词和 logprobs
暴露方式不同，所以该后端是本地 logits 路径的近似实现。

## 从二元分数到最终答案

对一个候选，后端会得到：

```text
q = exp(yes_logit) / (exp(yes_logit) + exp(no_logit))
```

MyJev 随后按问题分组这些分数：

| 题型 | 二元评分 | 最终结果 |
| --- | --- | --- |
| `Choice` | 每个选项一个判断 | 归一化分数，返回分布和最高选项 |
| `Score` | 每个等级一个判断，等级从 0 开始 | 归一化分数，计算等级的加权平均值 |
| `Noul`，无 criteria | 直接判断原问题 | 返回 yes 分数 |
| `Noul`，有 criteria | 分别判断 `true` 和 `false` 的含义 | 归一化两者分数，返回 `true` 分数 |

例如，Choice 的原始分数 `[0.2, 0.8, 0.2]` 归一化后约为
`[0.167, 0.667, 0.167]`。Score 的分布 `[0.2, 0.7, 0.1]` 会得到最终分数
`0.9`。这些只是计算示例，不是实测模型输出。

`Choice` 并列时按原 `criteria` 顺序选择第一项。`Score` 的等级顺序本身定义了
评分含义，不会重排。所有原始分数都是 0 时，MyJev 返回均匀分布。

## Confidence

对 `Choice` 和 `Score`，confidence 描述归一化后的候选分布有多集中。设候选
数量为 `n`，最大候选概率为 `p_max`，MyJev 计算：

```text
当 n = 1 时，confidence = 1；当 n > 1 时：

```text
confidence = (n * p_max - 1) / (n - 1)
```
```

结果限制在 `[0, 1]`。均匀分布的 confidence 是 0；概率全部集中在一个候选时
是 1。它描述的是本次答案分布的性质，不是经过校准的“判断一定正确”的概率。
`Noul` 没有单独的 confidence 字段。

## 成本与复用

独立候选会重复 `state` 和问题说明。候选越多、材料越长，逻辑输入 token 数
越大。对应的收益是：最终答案分布本身不需要逐 token 生成，因此在这个阶段
避免了 decode 时间和解析模型 JSON 的风险。

使用 SGLang 时，公共前缀可以只计算一次并被后续候选复用。详见
[共享前缀提交](shared-prefix-cache_zh.md)。
