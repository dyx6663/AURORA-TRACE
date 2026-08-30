# 设计说明：为什么 AURORA TRACE 不像普通 Coding Agent

## 1. 观察到的常见路线

公开的编程智能体通常集中在几种范式：

- SWE-agent：围绕软件工程 Issue，通过终端和编辑工具自动修复代码；
- OpenHands：提供更完整的开放式软件工程 Agent 环境；
- Aider：以终端为中心，用模型协助编辑 Git 仓库；
- ReAct 类方法：让模型在“思考—行动—观察”之间循环。

这些路线验证了工具调用闭环的有效性，但在考核演示中，如果只展示聊天记录、终端输出或最终 Diff，很容易与常见 Coding Agent 作品相似，也不容易让评委快速判断每一步为什么发生。

## 2. 本项目的差异化定位

AURORA TRACE 将“证据链”作为一等对象，而不是运行结束后的日志附属物。每个事件同时记录：

```text
decision → tool call → local result → verification evidence
```

因此项目演示的中心不是“模型很聪明”，而是：

> Agent 的每个外部动作都能被解释、追踪和复盘。

这使它更适合软件工程专业面试：评委可以从事件卡片、工具参数、Diff 和测试结果直接检查系统是否真的完成了任务。

## 3. 三个核心设计决策

当前版本进一步加入 Acceptance Contract。任务启动时，系统把“必须观察到什么证据”显式化为四个 Gate：基线故障、最小补丁、回归测试通过和工作区边界安全。最终 Confidence Score 由这些真实事件计算，而不是由模型自报。

### Evidence Ledger

运行过程中同时维护完整事件流和精简账本。事件流用于界面回放，账本用于回答“调用了哪些工具、修改了哪些文件、是否完成验证”。

### Run Workspace

每次运行都复制到 `.runs/<run_id>`，不直接污染种子项目。这样可以保证每次视频演示从同一初始状态开始，也能清楚计算 Diff。

### Guarded Executor

文件操作经过路径边界检查；命令采用 `shell=False`，只允许 Python、pytest、npm、node 前缀，并限制超时。Agent 的能力因此是“可执行但可控”的。

### Trace Export

每个 run 同时保留内存事件流、`evidence.ndjson` 和可下载 JSON。前者服务于实时界面，后两者服务于复盘、提交材料和后续实验统计。

## 4. 面试时的核心回答

**问：为什么不直接让模型输出代码？**

答：因为编程任务需要读取真实上下文、修改真实文件并运行验证。模型负责决策，本地执行器负责事实，测试结果再反馈给模型，二者形成闭环。

**问：为什么需要 Evidence Ledger？**

答：普通日志只能说明发生了什么，Ledger 还保留事件之间的关联，让每次修改都能追溯到决策理由和验证结果。这是面向软件工程可靠性的设计。

**问：如何防止无限循环？**

答：以 `finish`、异常失败和最大 12 次迭代作为终止条件；每次工具调用都产生结构化结果，模型不能通过自由文本绕过循环控制。

**问：是否使用了 Agent 框架？**

答：没有。项目只使用 Python 标准库和模型的 HTTP 接口；工具注册、JSON 解析、上下文、循环、执行器和前端事件流均为自行实现。

## 5. 参考入口

- SWE-agent: <https://github.com/SWE-agent/SWE-agent>
- OpenHands: <https://github.com/All-Hands-AI/OpenHands>
- Aider: <https://github.com/Aider-AI/aider>
- ReAct: <https://arxiv.org/abs/2210.03629>
- SWE-bench: <https://www.swebench.com/>

以上链接用于了解公开技术路线；本项目没有复制这些项目的代码或依赖其 Agent 框架。
