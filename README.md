# AURORA TRACE

> 当前升级版入口 / Current upgraded entry: `web/console.html` 由 `python aurora.py` 在 `/` 提供。

本项目当前将自己定义为“面向软件工程任务的证据驱动型 Coding Agent 实验平台”，重点不是让模型生成更多代码，而是让每一次决策、工具调用、文件变更和测试结果都能被解释、验证、追溯和回放。

升级后的核心材料：

- [ARCHITECTURE.md](ARCHITECTURE.md)：分层架构、事件结构和系统边界；
- [EVALUATION.md](EVALUATION.md)：可复现实验协议、负向控制和消融设计；
- [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)：关键工程决策与取舍；
- [PROGRESS.md](PROGRESS.md)：真实已完成能力与明确未实现能力。

> Evidence-first local coding agent — 一个可审计、可回放的本地编程智能体。

AURORA TRACE 通过 OpenAI 兼容模型接口理解编程任务，自主调用本地文件与命令工具，在隔离的任务工作区中完成修改，并实时生成一条可回放的证据链：`决策 → 工具 → 结果 → 验证`。

## 亮点

- 不使用 LangChain、LlamaIndex、Agents SDK 或任何 Agent 框架；Agent 循环、上下文、工具注册、解析、执行和终止条件全部自行实现。
- Evidence Ledger：每次行动都有时间、理由、输入、输出摘要和状态，避免“只展示最后代码”的黑箱演示。
- Adaptive Acceptance Contract：根据 Bug 修复、功能新增、结构重构或一般变更选择不同的基线策略；修复任务要求复现失败，新增/重构任务要求先确认绿色基线。
- Replayable Run：每个任务在独立 run workspace 中执行，自动捕获修改前后 Diff，能够回放完整过程。
- Exportable Trace：运行结束后可导出结构化 JSON 轨迹；`.runs/<run_id>/` 中同步保留 `run.json` 与 `evidence.ndjson`，Agent 只能访问其下的 `workspace/`。
- Project Intake：可从网页导入不超过 10 MB 的 ZIP 项目；系统进行 Zip Slip 检查、限制解压大小，并自动生成语言与测试命令画像。
- Guarded Workspace：文件访问限制在任务工作区内；命令执行使用白名单和超时。
- Approval Gate：手动模式下，写文件、精确替换和命令执行必须先经过人工授权；审批结果进入 Evidence Ledger。
- Verified Apply：导入项目在副本中完成并通过验收后，系统自动校验原项目未被外部修改，再将已验证的最小补丁写回，并保留写回前备份；用户不需要重复确认任务结果。
- Cooperative Cancellation：运行可以从页面或 API 请求取消；审批等待和长命令都会被协作式唤醒或中断，并落为 `CANCELLED` 终态。
- Mock Demo：无需 API Key 即可演示完整闭环；页面也提供 Live 模式，可切换到真实 OpenAI-compatible API。
- Evidence-aware Context Budget：长任务压缩旧的源代码/命令输出，但保留消息结构、工具状态和验证事实，避免上下文无限膨胀。
- 证据控制台界面，包含运行状态、验收策略、证据流、Run History、Replay、Diff 和验证结果。

## 运行

需要 Python 3.10+，仅使用标准库：

```powershell
cd aurora-trace
python aurora.py
```

浏览器打开 <http://127.0.0.1:8765>，选择内置 Todo 项目、`Bug 修复 · 需要复现失败` 和 `Mock Demo · 无需 API Key`，点击“开始受控运行”即可观看完整演示。运行时支持自动授权、手动审批和协作式取消；对于导入的真实项目，验收通过后系统会自动校验并写回已验证补丁，无需在每一次 Agent 操作前重复确认。验收策略也可以选择自动识别、功能新增、结构重构或一般变更；后面三类策略需要使用 Live Model，因为内置 Mock 夹具只对应这个故意失败的 Bug 修复任务。

处理自己的项目：在左侧“项目来源”点击“导入 ZIP”。导入项目会持久化到本地 `projects/`，每次运行先复制到新的 `.runs/<run_id>/workspace/`，Agent 不会在执行过程中直接改动原始导入文件。通过验收后，系统自动校验原项目没有被外部修改，将已验证的文件变更写回，并在运行目录保留写回前备份；若原项目在运行期间发生变化，系统会拒绝写回并保留 Diff 供处理。上传项目需要使用 Live 模式和模型 API；内置 Todo 项目可以使用稳定 Demo 模式。

真实模型模式（PowerShell）：

```powershell
$env:AURORA_MODE = "live"
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:AURORA_MODEL = "gpt-4o-mini"
python aurora.py
```

API Key 只通过环境变量读取，不会写入项目文件或运行记录。

## 演示任务

默认 Demo 会让 Agent 修复一个 Todo 项目的删除边界 Bug，并运行 `python -m unittest discover -s tests -v`。演示中可以看到：扫描项目、读取代码、形成基线假设、先复现失败、写入补丁、再次测试、验收 Gate 最终通过。对于功能新增或结构重构任务，系统会将“基线故障”解释为“绿色基线已确认”，避免把 Bug 修复规则错误套用到所有任务；若在 Mock 模式选择了不匹配的任务类型，系统会在复制工作区前明确拒绝并提示切换 Live Model。

## 核心架构

```text
Browser Console → HTTP API → Agent Controller → Model Adapter
                                      ↓
                              contract gate + Tool Registry / Executor
                                      ↓
                       isolated workspace + evidence ledger
```

模型只负责下一步决策；策略层决定高风险工具是否需要人工审批；本地执行器负责真实文件和命令操作；执行结果再次进入上下文。Agent 在 `finish`、失败、用户取消或达到最大迭代次数时停止。

## 项目结构

```text
aurora.py                 # 标准库 HTTP 服务、Agent、工具、契约和模型适配器
web/console.html          # 当前 UTF-8 控制台页面
web/console.js            # 事件轮询、契约、History、Replay 与状态可视化
web/console.css           # 当前控制台视觉系统
web/style.css             # 视觉系统
seed_project/             # 演示用的故意含 Bug 项目
projects/                 # 本地导入项目（已被 .gitignore 排除）
tests/                    # Agent 核心安全与契约测试
VIDEO_SCRIPT.md           # 两分钟演示脚本与答辩要点
PROJECT_BILINGUAL.md      # 中英双语项目说明
RESEARCH_NOTES.md         # 公开路线检索与差异化记录
```

## 约束说明

命令执行器只开放 Python、测试等受限命令，并设置路径边界与超时保护。运行不可信代码前，仍建议在专用本地目录中进行隔离。
