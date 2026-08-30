# AURORA TRACE 开发过程记录

> 本文件用于记录项目的真实开发、验证与提交安排。表中的“计划”不是已经发生的提交；只有完成对应工作并通过检查后，才会执行 commit 和 push。

## 仓库现状

| 项目 | 当前情况 |
|---|---|
| 本地仓库 | 已建立，分支为 `main` |
| 当前提交 | `85aaf82` · `docs: record reproducible development plan` |
| 初始快照 | `412efff` · `建立 AURORA TRACE 初始版本`（2026-08-30 21:15:16 +08:00） |
| 远程仓库 | 尚未绑定 GitHub/Gitee 地址 |
| 公开地址 | 待创建公开仓库后填写到 `README.txt` |
| 历史处理原则 | 不倒签、不压缩、不改写已推送历史 |

当前初始提交是项目完成后的完整快照，不能被表述为“从零开始逐步提交”的历史。后续提交将记录真实发生的文档补充、工程改进和验证结果。

## 分阶段提交计划

时间以中国标准时间（UTC+8）为准；具体提交时间应以实际完成时间为准，不能使用未来时间或人为修改时间。

| 顺序 | 时间安排 | 提交内容 | 主要文件 | 提交后可展示的证据 | 状态 |
|---:|---|---|---|---|---|
| 0 | 2026-08-30 21:15 | 建立项目初始快照 | `aurora.py`、`web/`、`seed_project/`、`tests/` | 项目可以启动，内置 Demo 可以完成一次闭环 | 已完成 |
| 1 | 2026-08-30 22:46 后 | 补充可复现开发记录与提交规范 | `DEVELOPMENT_LOG.md` | 展示项目现状、真实历史边界和后续实验安排 | 本次提交 |
| 2 | 2026-08-30 23:00 左右 | 完成第一轮工程验证记录 | `tests/`、`README.md` 或新增验证记录 | `python -m unittest discover -s tests -v`、Python/JavaScript 语法检查结果 | 计划，完成后再提交 |
| 3 | 2026-08-31 上午 | 完成项目导入与隔离边界专项验证 | `aurora.py`、`tests/`、相关说明文档 | ZIP 导入、Zip Slip 拦截、路径越界拦截、命令限制结果 | 计划 |
| 4 | 2026-08-31 下午 | 完成前端与演示流程收尾 | `web/index.html`、`web/app.js`、`web/polish.css`、`VIDEO_SCRIPT.md` | 页面加载、Demo 执行、Diff、回归测试、Trace 导出截图或视频 | 计划 |
| 5 | 截止时间前 | 写入真实公开仓库地址并完成最终推送 | `README.txt`、必要的最终说明 | README 地址、远程分支、提交记录、最终测试结果 | 等待仓库地址 |

## 推荐的两次推送安排

### 第一波：今晚

第一波的目标是建立“项目现状 + 可复现实验”的记录，不追求堆砌提交数量。

1. 提交本文件，固定当前仓库状态和后续安排。
2. 运行核心测试、语法检查和一次内置 Demo。
3. 只有当新增了真实验证记录或真实工程改进时，才提交第二个 commit。
4. 推送后记录远程仓库 URL、分支名和 commit hash。

建议的真实提交信息：

```text
docs: record reproducible development plan
test: record initial verification results
```

第二条提交只有在确实新增测试或验证材料后才使用，不能为了制造“过程感”提交空改动。

### 第二波：明天

明天的推送应当围绕能够现场演示的证据展开：

1. 完成 ZIP 导入、路径边界、命令白名单和工作区隔离的专项验证。
2. 完成前端操作路径复核，确保“导入项目 → 执行任务 → 查看 Diff → 查看测试 → 导出 Trace”可连续操作。
3. 更新视频脚本，使每个画面都对应一个真实功能和一个真实结果。
4. 绑定公开 GitHub/Gitee 仓库地址，写入 `README.txt`。
5. 运行最终检查后再推送最后一波；截止时间之后不再推送。

建议的真实提交信息：

```text
test: verify project intake and workspace boundaries
docs: align demo script with verified workflow
docs: add public repository link
```

## 每次提交前检查

```powershell
python -m py_compile aurora.py
node --check web/app.js
python -m unittest discover -s tests -v
git status --short
git log --oneline --decorate -5
git remote -v
```

提交后应保存以下信息：

| 信息 | 用途 |
|---|---|
| commit hash | 证明提交顺序和内容对应关系 |
| 提交时间 | 与题目截止时间进行核对 |
| 测试命令及结果 | 证明该阶段不是只提交文档 |
| 公开仓库 URL | 供评委访问源码和提交历史 |
| 视频时间点 | 将演示画面对应到具体功能 |

## 诚实性说明

本项目不能通过倒签、批量制造空提交、修改作者时间或重写历史来模拟不存在的开发过程。若需要让评委更容易理解建模过程，应使用架构说明、测试记录、Diff、事件账本和视频章节补充证据，而不是伪造提交历史。
