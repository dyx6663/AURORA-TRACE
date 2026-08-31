# AURORA TRACE
## 双语项目说明 / Bilingual Project Brief

> 版本 / Version: 0.1.0  ·  定位 / Positioning: Evidence-first Local Coding Agent

## 1. 项目概述 / Project Overview

**中文**：AURORA TRACE 是一个个人独立设计并实现的本地编程智能体。它接收自然语言编程任务，通过大语言模型选择工具，在隔离工作区内读取和修改代码、执行测试，并将整个过程记录为可审计、可回放的证据链。

**English**: AURORA TRACE is an independently designed and implemented local coding agent. Given a natural-language programming task, it uses an LLM to select tools, reads and edits code inside an isolated workspace, runs verification commands, and records the complete process as an auditable and replayable evidence chain.

## 2. 设计主张 / Design Thesis

**中文**：普通 Coding Agent 的演示重点往往是“最终生成了什么代码”。AURORA TRACE 将重点前移：每个外部动作都必须回答三个问题——为什么做、做了什么、凭什么认为完成。系统把 `决策 → 工具 → 结果 → 验证` 作为一次完整的工程事件。

**English**: Typical coding-agent demos focus on what code was finally generated. AURORA TRACE moves the focus upstream: every external action must answer three questions—why it was taken, what it changed, and what evidence supports completion. The system treats `decision → tool → result → verification` as one engineering event.

这使项目从“模型驱动的代码生成器”变成“面向软件工程可靠性的可观察执行系统”。

This turns the project from a model-driven code generator into an observable execution system designed around software-engineering reliability.

## 3. 与常见方案的差异 / Differentiation

| 维度 / Dimension | 常见实现 / Common implementation | AURORA TRACE |
| --- | --- | --- |
| 交互中心 / Center | 聊天记录或终端 / chat or terminal | 证据事件流 / evidence stream |
| 修改记录 / Changes | 最后展示 Diff / final diff | 每次写入立即绑定 Diff / Diff attached to each write |
| 完成判断 / Completion | 模型口头宣布完成 / model says done | 测试结果与终止事件 / tests plus terminal event |
| 运行环境 / Runtime | 直接操作项目 / direct project access | 每次运行独立 workspace / isolated run workspace |
| 可解释性 / Explainability | 事后日志 / retrospective logs | 决策理由与工具参数同步记录 / reason and arguments recorded together |
| 安全边界 / Safety | 依赖外部框架 / framework-dependent | 路径边界、命令白名单、超时 / path guard, allowlist, timeout |

这里的创新不是声称发明了全新的 LLM 算法，而是将“证据链”和“可回放运行”作为 Coding Agent 的核心产品与工程抽象。这一定位真实、可实现，也适合现场答辩。

The novelty is not a claim of inventing a new LLM algorithm. It is the engineering abstraction of an evidence chain and replayable runs as first-class components of a coding agent. This is both honest and defensible in an interview.

## 4. 系统架构 / System Architecture

```text
Browser Console / 浏览器控制台
            ↓
HTTP API / 任务入口
            ↓
Agent Controller / Agent 控制器
            ↓
Model Adapter / 模型适配器
            ↓
Decision Parser / 决策解析器
            ↓
Tool Registry + Guarded Executor / 工具注册与受控执行器
            ↓
Run Workspace + Evidence Ledger / 隔离工作区与证据账本
```

**中文**：模型只负责选择下一步行动；本地执行器负责文件和命令这一事实层操作；结果重新加入上下文，形成闭环。

**English**: The model only selects the next action. The local executor performs factual file and command operations. Results are fed back into context to close the loop.

用户可以直接从网页导入 ZIP 项目。系统验证归档路径以防止 Zip Slip，限制上传与解压体积，自动识别主要语言和可用测试命令，然后为每次任务创建独立运行副本。

Users can import a ZIP project directly from the web interface. The system validates archive paths against Zip Slip, limits upload and extraction sizes, detects primary languages and candidate test commands, and creates an isolated copy for every run.

## 5. 工具与控制逻辑 / Tools and Control Logic

当前实现提供五个本地工具：

The current implementation exposes five local tools:

- `list_files`：建立项目地图 / build a project map
- `read_file`：读取真实上下文 / read real context
- `write_file`：写入代码并生成 Unified Diff / write code and generate a unified diff
- `run_command`：执行白名单命令并捕获输出 / run allowlisted commands and capture output

此外，`replace_text` 只允许对一个唯一匹配进行精确替换，并直接返回最小 Diff。运行开始时还会建立 Adaptive Acceptance Contract：Bug 修复任务核验基线失败，功能新增、重构和一般变更任务核验绿色基线；四类任务都要求最小补丁、回归测试通过和工作区边界安全。

In addition, `replace_text` only applies an exact replacement when there is one unique match and returns a minimal Diff. Each run also creates an Adaptive Acceptance Contract: repair tasks require an observed baseline failure, while feature, refactor and general-change tasks require a green baseline. All four types still require a minimal patch, a passing regression test and workspace-boundary compliance.

终止条件 / Termination conditions:

1. 模型返回 `finish` / the model returns `finish`;
2. 工具或模型发生不可恢复错误 / an unrecoverable tool or model error occurs;
3. 达到最大 12 次迭代 / the 12-iteration ceiling is reached.

安全控制 / Safety controls:

- 所有路径必须位于当前 run workspace 内，审计文件位于 Agent 不可见的上层 / all paths must remain inside the run workspace, while audit files stay outside the Agent-visible child directory;
- 命令使用 `shell=False` / commands use `shell=False`;
- Evidence Ledger 同步写入运行目录根部的 `evidence.ndjson`，并可导出 JSON Trace / the Evidence Ledger is persisted at the run root and exportable as JSON;
- 只允许 `python`、`pytest`、`npm`、`node` 前缀 / only selected command prefixes are allowed;
- 禁止 shell chaining、重定向和 20 秒以上执行 / chaining, redirection, and executions over 20 seconds are blocked.

## 6. 演示任务 / Demonstration Task

**中文任务**：

> 修复 Todo 项目的删除边界 Bug，运行回归测试，并给出修改证据。

**English task**:

> Fix the Todo deletion boundary bug, run the regression tests, and provide evidence for the change.

默认项目在 `remove(index)` 中故意使用错误的边界条件。演示流程如下：

The seed project intentionally contains an incorrect boundary condition in `remove(index)`. The demo flow is:

```text
UNDERSTAND
  → list_files
  → read_file(todo.py)
  → read_file(test_todo.py)
  → run_command  (reproduce the failure)
  → write_file   (minimal patch)
  → run_command  (regression verification)
  → VERIFIED
  → FINISH
```

最终证据是 5 项单元测试全部通过，而不是模型的一句自我判断。

The final evidence is five passing unit tests—not a verbal claim from the model.

## 7. 对导师的价值 / Why It Matters to a Research-Oriented Reviewer

**中文**：这个项目体现的不是调用 API 的能力，而是把不确定的模型行为约束进一个可观察的软件系统的能力：明确状态、定义工具协议、隔离副作用、记录证据、使用测试闭环验证。这些能力可以自然延伸到软件工程智能体评测、可靠性、可复现性和人机协作研究。

**English**: The project demonstrates more than API integration. It shows how to constrain uncertain model behavior inside an observable software system: explicit states, a tool protocol, isolated side effects, evidence recording, and test-based verification. These ideas naturally extend to research on software-engineering agents, reliability, reproducibility, and human–AI collaboration.

## 8. 诚实的能力边界 / Honest Limitations

**中文**：当前版本是一个完成考核目标的可复现原型，而不是生产级代码沙箱。Mock 模式用于保证视频演示稳定；Live 模式用于展示真实模型调用。当前已实现高风险工具人工审批和协作式取消；代码搜索、测试选择、分支级隔离等仍属于后续方向，不应在短视频中堆砌未验证功能。

**English**: The current version is a reproducible prototype that satisfies the assessment target, not a production-grade code sandbox. Mock mode guarantees a stable recording; Live mode demonstrates real model integration. High-risk tool approval and cooperative cancellation are implemented; code search, test selection, and branch-level isolation remain future directions. Unverified features should not be overclaimed in a short video.

## 9. 推荐答辩表述 / Recommended Defense Statement

**中文**：

> 我没有把重点放在让模型生成更长的代码，而是放在让每个动作都可解释、可验证、可复现。模型是决策者，工具执行器是事实层，测试是验收层，Evidence Ledger 是审计层。这样即使模型犯错，系统也能通过真实执行结果发现问题并停止或继续修复。

**English**:

> I did not optimize for generating longer code. I optimized for making every action explainable, verifiable, and reproducible. The model is the decision-maker, the tool executor is the factual layer, tests are the acceptance layer, and the Evidence Ledger is the audit layer. Even when the model is wrong, the system can use real execution results to detect the error and either continue repairing or stop safely.

## 10. 相关公开路线 / Publicly Known Directions

- SWE-agent: <https://github.com/SWE-agent/SWE-agent>
- OpenHands: <https://github.com/All-Hands-AI/OpenHands>
- Aider: <https://github.com/Aider-AI/aider>
- ReAct: <https://arxiv.org/abs/2210.03629>
- SWE-bench: <https://www.swebench.com/>

本项目借鉴公开领域问题意识，但没有使用这些项目的代码或 Agent 框架。

The project is informed by these public directions but does not use their code or agent frameworks.
