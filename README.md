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
- Acceptance Contract：运行开始时锁定验收条件，核验基线失败、最小补丁、回归通过和工作区安全边界，实时计算 Evidence Confidence。
- Replayable Run：每个任务在独立 run workspace 中执行，自动捕获修改前后 Diff，能够回放完整过程。
- Exportable Trace：运行结束后可导出结构化 JSON 轨迹；workspace 中同步保留 `evidence.ndjson`。
- Project Intake：可从网页导入不超过 10 MB 的 ZIP 项目；系统进行 Zip Slip 检查、限制解压大小，并自动生成语言与测试命令画像。
- Guarded Workspace：文件访问限制在任务工作区内；命令执行使用白名单和超时。
- Mock Demo：无需 API Key 即可演示完整闭环；页面也提供 Live 模式，可切换到真实 OpenAI-compatible API。
- 高级深色控制台界面，包含运行状态、证据流、文件树、Diff 和验证结果。

## 运行

需要 Python 3.10+，仅使用标准库：

```powershell
cd aurora-trace
python aurora.py
```

浏览器打开 <http://127.0.0.1:8765>，选择内置 Todo 项目和“稳定演示 / DEMO”，点击“开始执行”即可观看完整演示。

处理自己的项目：在左侧“项目来源”点击“导入 ZIP”。导入项目会持久化到本地 `projects/`，每次运行仍会复制到新的 `.runs/<run_id>/`，不会直接修改原始导入文件。上传项目需要使用 Live 模式和模型 API；内置 Todo 项目可以使用稳定 Demo 模式。

真实模型模式（PowerShell）：

```powershell
$env:AURORA_MODE = "live"
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:AURORA_MODEL = "gpt-4o-mini"
python aurora.py
```

API Key 只通过环境变量读取，不要提交到仓库、README 或视频中。

## 演示任务

默认 Demo 会让 Agent 修复一个 Todo 项目的删除边界 Bug，并运行 `python -m unittest discover -s tests -v`。演示中可以看到：扫描项目、读取代码、先复现失败、写入补丁、再次测试、最终通过。

## 核心架构

```text
Browser Console → HTTP API → Agent Controller → Model Adapter
                                      ↓
                              contract gate + Tool Registry / Executor
                                      ↓
                       isolated workspace + evidence ledger
```

模型只负责下一步决策；本地执行器负责真实文件和命令操作；执行结果再次进入上下文。Agent 在 `finish`、失败或达到最大迭代次数时停止。

## 项目结构

```text
aurora.py                 # 标准库 HTTP 服务、Agent、工具和模型适配器
web/index.html            # 控制台页面
web/app.js                # 事件轮询、Diff 与状态可视化
web/style.css             # 视觉系统
seed_project/             # 演示用的故意含 Bug 项目
projects/                 # 本地导入项目（已被 .gitignore 排除）
tests/                    # Agent 核心安全与契约测试
VIDEO_SCRIPT.md           # 两分钟演示脚本与答辩要点
PROJECT_BILINGUAL.md      # 中英双语项目说明
RESEARCH_NOTES.md         # 公开路线检索与差异化记录
```

## 约束说明

这是一个教学与考核演示项目。命令执行器只开放 Python/测试等安全命令，仍建议在本地专用目录运行，不要把不可信代码交给 Agent 执行。
