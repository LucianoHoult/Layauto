# 当前工作入口

更新：2026-09-08。此文件由 PM 维护当前节点和恢复入口；正式任务的详细状态与证据归对应任务文件。

## 当前节点

最小运行规范第一版已写入工作区，待用户另开会话做针对性 review。用户已授权本轮文档修改，明确要求 **不要 commit**；本轮也不推送或合并。

首次规范 review 采用下方文档范围，无任务编号。尚未建立 `docs/roadmap.md` 或实际任务文件；v2 产品开发、架构正文拆分、真实 EDA 环境部署均未由本轮启动。规范写入不代表已完成新会话恢复演练或生产能力验证。

## 本次 review 的恢复点

- 仓库：Layauto；编写时 branch 为 `main`，HEAD 为 `a25a011d8b4c48bfb4e4ce79d288ce7eefa12e77`。恢复时重新核对，不能只靠此记录。
- 入口：[AGENTS.md](../AGENTS.md) → [协作规则](collaboration/rules.md) → 本页 → 明确的被审文档及相关架构条款。
- 被审主文件：[协作规则](collaboration/rules.md)、[任务模板](collaboration/task-template.md)、本页及 [文档导航](README.md)。
- 联动文件：[项目 README](../README.md)、[本地环境](environment/local-setup.md)、[跨设备说明](environment/remote-development.md)、[旧提案状态及引用](proposals/v2-codex-development-workflow.md)。
- 环境文档由旧 `docs/development.md`、`docs/remote-development.md` 移位并整理。旧文件本来未跟踪，Git 不会自动提供其重命名前 diff。
- `.gitignore` 与 `pyproject.toml` 的现有改动来自更早的环境配置，本轮保留原样；README、AGENTS、环境文档和旧提案也已有未提交版本，本轮在其基础上修改。`docs/architecture.md` 与业务代码不是本次修改范围。

检查时同时使用 `git diff HEAD`、`git status --short` 和 `git ls-files --others --exclude-standard`；新增文件须直接读取，不能把 `git diff` 看成完整范围。

本次未提交，请在同一 checkout 的本地新会话审阅；新 worktree 或 cloud 不保证持有这些草案。已保存[编写前对照清单](/var/folders/7p/py58pz81089d2h4vn7nrf3h00000gn/T/layauto-workflow-baseline-s42u7_l5/manifest.json)和[待审快照清单](/var/folders/7p/py58pz81089d2h4vn7nrf3h00000gn/T/layauto-workflow-baseline-s42u7_l5/review-snapshot/manifest.json)，各文件副本位于对应清单目录，附 SHA-256；仅用于本机短期交接。接手者核对快照与工作区是否一致，若不一致，明确本次实际审阅的版本。

## 本轮自查与限制

文档本地链接/锚点、代码块闭合、示例 shell 语法和 diff 空白检查通过；`.gitignore`、`pyproject.toml`、架构正文与本轮起点字节一致，HEAD 未变、暂存区无差异。内部 reviewer 已检查入口、职责和交接，并据此澄清 finding 处理列归属；这不替代下一次独立 review。未执行产品测试、环境安装、真实工具验证或实际新会话恢复演练。

## 当前授权与下一步

下一角色为 **review**：只读检查上述第一版，输出具体 findings、文件位置、影响、建议和未验证范围；本次独立 review 结果先留在该 review 会话，交 PM 接收，不自行修改或提交文件。

可用启动指令：

> 按项目规范，review `docs/current-work.md` 指定的最小运行规范第一版。检查全部相关未提交及未跟踪文件，只读，不 commit。重点核对角色/上报边界、文件权威、无任务编号和未提交状态下的恢复路径，以及模板能否完整承接执行、review 与 PM 验收。

PM 接收时核对 review 对应的文件版本及实际 findings，在授权范围内修复；若变更了用户已确认的协作预期，先给出具体差异。交接到另一会话前把本次 review 的可访问位置、目标版本和处置结论补入本页；正式任务建立后迁入对应任务记录，入口只留链接。

后续全局路线和首个任务由正式规划产生。真实工具/PDK 的选择仍是待评估事项；这里不以旧提案的候选切片或环境讨论替代排期及技术验证。
