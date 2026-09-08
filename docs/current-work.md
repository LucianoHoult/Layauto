# 当前工作入口

更新：2026-09-08。此文件由 PM 维护当前节点和恢复入口；正式任务的详细状态与证据归对应任务文件。

## 当前节点

最小运行规范第一版已完成独立 review，未发现实质问题，文档交付已验收。2026-09-08 用户随后授权“把需要 commit 的合并入 main”；该授权取代编写和只读 review 阶段的“不提交”限制。

已审原稿及配套环境配置位于 `main` 提交 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，本页补充验收和恢复记录。尚未建立 `docs/roadmap.md` 或实际任务文件；本轮未启动 v2 产品开发、架构正文拆分或真实 EDA 环境部署。

## 首次规范 review 与验收记录

- Reviewer：2026-09-08 本次独立 Codex review 会话，按用户指定范围只读检查；随后按用户新授权接收结果并集成。
- 审阅基线：`main@a25a011d8b4c48bfb4e4ce79d288ce7eefa12e77`，暂存区为空。检查了 tracked diff 与全部 7 个 untracked 文件。
- 快照身份：11 个文件的工作区、副本及 SHA-256 全部一致，提交前再次核对。原待审清单 SHA-256 为 `2a8305a435ead2a2c961ca71917b52049b90f7353791446887eab5408a6ea1f1`；上述 `e57f2dd` 提交逐文件保留了同一内容，后续恢复使用该 Git 版本，无需依赖本机临时目录。
- 被审主文件：[协作规则](collaboration/rules.md)、[任务模板](collaboration/task-template.md)、本页及 [文档导航](README.md)。
- 联动文件：[根 AGENTS](../AGENTS.md)、[项目 README](../README.md)、[本地环境](environment/local-setup.md)、[跨设备说明](environment/remote-development.md)、[旧提案状态及引用](proposals/v2-codex-development-workflow.md)，以及 `.gitignore`、`pyproject.toml`。
- Review 结论：无实质 findings。职责与 finding 写入归属清楚，普通问题由内部处理；文件未形成平行权威；无编号 review 和未提交快照可恢复；模板覆盖方案、执行、独立 review、修复复核及 PM 验收。新的关键使用预期需要用户判断，技术保真、legacy 取用及真实工具证据仍须独立核验，不能由自造 golden 通过替代。
- 改动归属：`.gitignore`、`pyproject.toml` 来自更早的环境配置，规范编写时保持原样；README、AGENTS、环境文档及旧提案也已有草稿。已直接对照编写前副本，包含旧 `docs/development.md`、`docs/remote-development.md` 到 `docs/environment/` 的迁移。环境配置经补充检查后作为安装说明的配套依赖一并提交；架构正文与业务代码未变。
- PM 验收：已核对实际材料、版本、review 结论及下列验证范围，无待处理 finding 或新的协作预期待决项。原稿提交后仅更新本页和旧提案的审阅状态，不改变已审协作规则、模板或产品合同。

首次 review 无任务编号，按初始化例外在本页保存记录。原恢复点和当时授权可用 `git show e57f2dd:docs/current-work.md` 查阅；正式任务建立后，其详细状态与证据归任务文件。

## 验证与限制

验证绑定上述原稿提交；本页和旧提案的状态更新另做链接及 diff 检查，并经独立 reviewer 复核，无实质问题。文档检查使用本机 `$HOME/.virtualenvs/layauto/bin/python`，未安装依赖或运行产品回归。

| 检查 | 方法与结果 | 限制 |
| --- | --- | --- |
| 文档及恢复 | 直接读取新增文件，核对相关架构条款、56 个本地链接、1 个锚点、代码块闭合、5 个 shell 块的 `bash -n` 和 `git diff --check`，均通过；本会话已按入口找到无编号 review 及其快照 | 未演练正式任务的执行 → review → 修复 → PM 验收完整周期 |
| 跨主机说明 | 对照文档中链接的 OpenAI Remote / cloud 官方原文，关键运行位置和交接限制一致 | 未实际配置或验证 Remote 配对、SSH、cloud 环境 |
| 包配置 | 在临时源码副本中以 Python 3.11.5 / setuptools 65.5.0 调用 `setuptools.config.pyprojecttoml.read_configuration()` 和 `setuptools.build_meta.build_sdist()`；只发现 11 个 `layauto_v2` 包，归档中的 58 个 Python 文件路径与 v2 源码完全对应，无 legacy 包 | 这不是产品正确性或真实工具能力验证 |
| Wheel 构建 | pip 23.2.1 执行 `python -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir <临时输出> .`，因环境缺 `wheel` 而未通过；后端 `get_requires_for_build_wheel({})` 返回 `["wheel"]` | 未安装该动态依赖，未验证 wheel、标准隔离构建或新主机安装，不把本次失败记为通过 |

真实 EDA 工具、PDK/profile、商业许可证、产品能力与生产正确性均未由本轮验证。历史 legacy 测试结果继续按环境文档的日期和限制理解。

## 恢复与下一步

从 [AGENTS.md](../AGENTS.md) → [协作规则](collaboration/rules.md) → 本页恢复。先核对 checkout、branch、HEAD、工作区及目标提交可访问性；当前验收记录的提交可用 `git log -1 --format=%H -- docs/current-work.md` 定位。跨主机需取得包含原稿及本页验收更新的提交，不沿用旧的临时快照路径。

下一角色为 **PM**，下一工作是正式规划首版路线图和近期任务；尚无任务编号、已确认排期或真实工具/PDK 选择。本轮止于规范与配套环境配置的集成。

后续启动指令：

> 按项目规范，以 PM 角色恢复当前工作，准备首版路线图和近期任务；既有架构内自主细化，新的关键预期或架构变化整理具体依据后交用户决定。
