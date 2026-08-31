# AURORA TRACE 视频演示脚本（≤ 2 分钟）

## 0:00–0:12｜一句话定位

“这是 AURORA TRACE，一个证据优先的本地编程智能体。它不只生成代码，还把每次决策、文件修改和测试结果组成一条可以回放的证据链。”

## 0:12–0:25｜界面扫过

展示左侧任务输入和 Acceptance Contract，中间 Evidence Stream，右侧 Evidence Confidence，底部 Diff 与 Verification。强调当前为 `SANDBOXED RUN`。

## 0:25–1:25｜运行 Demo

输入：

```text
修复 Todo 项目的删除边界 Bug，运行回归测试，并给出修改证据。
```

点击 `RUN DEMO`，可加速播放。重点保留这些事件：

1. `UNDERSTAND`：识别目标和验收条件；
2. `list_files`：扫描项目结构；
3. `read_file`：读取业务代码和测试；
4. `run_command`：先复现修改前的失败；
5. `replace_text`：写入最小精确补丁；
6. `run_command`：重新运行回归测试；
7. `finish`：生成完成摘要。

## 1:25–1:48｜展示证据链

点击 `EXPORT TRACE`，展示可下载的结构化 JSON 轨迹；打开 Diff，展示修改前后的代码；打开 Verification，展示测试命令和 `5 tests passed`。

## 1:48–2:00｜技术解释

“AURORA TRACE 的核心是我自己实现的控制循环。模型负责选择下一步工具，策略层先判断高风险操作是否需要人工授权，工具执行器再在隔离工作区中完成真实操作，并把结果加入上下文。验收契约把基线失败、最小补丁和回归通过变成可计算的证据 Gate；文件路径有边界检查，命令有白名单和超时，运行还支持人工审批和协作式取消。因此系统是可解释、可审计、可回放的。”
