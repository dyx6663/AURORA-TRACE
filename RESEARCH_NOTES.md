# AURORA TRACE 公开路线检索与差异化记录

检索日期：2026-08-28
检索类型：面向项目设计的技术 scoping review

## 研究问题

在不依赖现成 Agent 框架的前提下，如何把一个本地 Coding Agent 做得有辨识度、可解释、可验证，并适合两分钟视频与软件工程专业面试？

## 检索范围

检索了公开 GitHub 项目、arXiv 元数据和项目官方说明，重点关注：软件工程 Agent、Agent-Computer Interface、终端编码、ReAct 轨迹、SWE-bench、沙箱、评测和可观测性。

## 关键路线与启示

| 来源 | 公开路线 | 对本项目的启示 | 本项目的取舍 |
| --- | --- | --- | --- |
| SWE-agent, Yang et al., 2024 | 面向软件工程任务的 Agent-Computer Interface；读写文件、导航仓库、运行测试 | 工具接口会显著影响 Agent 行为和效果 | 自行实现小型 ACI，不复制其代码；增加证据账本和验收契约 |
| OpenHands, Wang et al., 2024 | 开放式软件开发 Agent；代码、命令行、浏览器、沙箱、多 Agent 和 benchmark | 开放环境与安全执行边界是重要工程问题 | 采用独立 run workspace 和受控执行器，保持项目可解释与可完成 |
| Aider | 终端协同编程、代码库地图、Git/Diff 工作流 | 代码上下文和 Diff 对实际协作很重要 | 保留 Diff 证据；不把项目做成终端 UI 克隆 |
| ReAct, Yao et al., 2022 | 交错进行 reasoning、acting、observation，形成可解释轨迹 | Agent 需要通过外部行动获得事实并处理异常 | 采用“决策—工具—结果”闭环；不展示或依赖隐藏思维链 |
| SWE-bench, Jimenez et al., 2023 | 用真实 GitHub Issue 和测试衡量代码修改能力 | 真实软件工程任务远比单次代码生成复杂 | 设计“先复现失败—最小修复—回归测试”的小型可证任务 |

## 差异化结论

公开路线已经普遍覆盖了“让模型使用工具完成代码任务”。因此，单纯增加工具数量、添加聊天窗口或堆叠多 Agent 并不能形成可靠差异。AURORA TRACE 的差异化选择是：

1. 把 Evidence Ledger 作为一等数据结构，而不是事后日志；
2. 用 Acceptance Contract 明确任务完成所需的证据 Gate；
3. 用真实测试结果计算 Evidence Confidence，而不是接受模型自报完成；
4. 每次运行复制到独立 workspace，并保留 NDJSON 和 JSON Trace；
5. 以最小精确替换工具降低补丁影响面，并输出可审计 Diff。

## 证据 Gate

一次成功运行必须满足：

- `baseline_failure_captured`：修改前失败被真实命令捕获；
- `minimal_patch_recorded`：至少产生结构化 Diff；
- `regression_tests_passed`：修改后回归测试返回成功；
- `workspace_boundary_respected`：执行未越过隔离工作区。

四项均满足时分数为 100。该分数只是本项目的可解释运行指标，不应表述为通用模型能力或 benchmark 成绩。

## 局限与后续

当前 Demo 是小型、确定性的本地任务，不能等价于 SWE-bench 级别的复杂修复；Mock 模式也不能冒充真实模型推理。正式演示应优先使用 Live 模式，Mock 模式仅作为网络/API 不稳定时的透明备用方案。后续如果有时间，可以加入人工审批、Git 分支隔离、代码搜索、测试选择和多次运行对比，但必须先实测再展示。

## 可核验参考

- Yang, J. et al. “SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering.” arXiv:2405.15793. <https://arxiv.org/abs/2405.15793>
- Wang, X. et al. “OpenHands: An Open Platform for AI Software Developers as Generalist Agents.” arXiv:2407.16741. <https://arxiv.org/abs/2407.16741>
- Yao, S. et al. “ReAct: Synergizing Reasoning and Acting in Language Models.” arXiv:2210.03629. <https://arxiv.org/abs/2210.03629>
- Jimenez, C. E. et al. “SWE-bench: Can Language Models Resolve Real-World GitHub Issues?” arXiv:2310.06770. <https://arxiv.org/abs/2310.06770>
- SWE-agent GitHub: <https://github.com/SWE-agent/SWE-agent>
- OpenHands GitHub: <https://github.com/All-Hands-AI/OpenHands>
- Aider: <https://github.com/Aider-AI/aider>

