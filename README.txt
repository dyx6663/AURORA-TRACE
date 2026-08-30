AURORA TRACE：一个证据优先的本地编程智能体

Git 仓库地址：待创建公开仓库后填写

一、运行方法
需要 Python 3.10+。进入项目目录后执行：
python aurora.py
浏览器访问 http://127.0.0.1:8765，选择内置 Todo 项目和“稳定演示 / DEMO”，点击“开始执行”。项目默认使用本地 Mock 演示，不需要 API Key。使用真实模型时，通过环境变量设置 AURORA_MODE=live、OPENAI_API_KEY、OPENAI_BASE_URL 和 AURORA_MODEL。

二、功能特色
AURORA TRACE 是一个可解释、可审计、可回放的 Coding Agent。它可以从网页导入 ZIP 项目，也可以使用内置 Demo；随后自主调用 list_files、read_file、replace_text、write_file 和 run_command，在独立工作区中修改代码并运行测试。系统将每次模型决策、工具参数、本地执行结果、代码 Diff 和验证结果写入 Evidence Ledger，并在网页控制台实时展示。界面采用中文主叙事和英文专业术语，方便中文评委理解。

项目没有使用 LangChain、LlamaIndex、OpenAI Agents SDK、Claude Agent SDK 或其他 Agent 框架。Agent 循环、上下文、工具注册、JSON 解析、本地执行、错误处理和最大迭代终止均由项目自行实现。文件操作有工作区边界检查，命令执行采用 shell=False、白名单和超时限制。

三、演示任务
默认演示项目包含一个 Todo 删除边界 Bug。Agent 会扫描项目、读取代码和测试、先复现失败、写入修复、再次执行单元测试，并在验证通过后给出完成摘要。完整的视频脚本和答辩要点见 VIDEO_SCRIPT.md，设计差异化说明见 DESIGN.md。

API Key 只通过环境变量读取，项目中没有保存任何真实凭据。
