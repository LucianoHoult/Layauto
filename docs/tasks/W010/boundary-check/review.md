# W010 依赖守卫修订独立复核

Reviewer：`/root/plan_review`，2026-11-05。未参与本次产品实现或守卫修订。范围仅为相对 `fba1e7be688c5fce88834dc8b859a8660bff6b7f` 的两个测试文件 diff，以及架构 §11.2、§11.3、§11.15 对应边界；不替代完整工程验证后的最终代码 review。

仓库 `/workspace/Layauto`，分支 `codex/w010-local-contact-connectivity`，review 时 HEAD 为上述基线。两个受审文件各有未提交修改，合计新增40行、删除1行；执行记录/工程证据附件正在由其他角色维护，不属于本报告写入范围。

| 受审文件 | 完整 SHA-256 |
| --- | --- |
| `tests/contracts/test_w007_contracts.py` | `08e05fcb26b8bd6d322f6ef26899d14ab2653b0e435d99214f3ccb65d2b8b37b` |
| `tests/contracts/test_w010_contracts.py` | `dab4868b5289c169043aec95bb6f41f7b2f17167f4f3ae3e3f1361e861432fc0` |

**结论：必须修正项0。修订保留原守卫实质，没有放宽 mutable state/publication 边界。**

## 审查依据与结果

1. 原 W007 守卫仍遍历全部 normalization 模块及原四个 domain 文件；原 `forbidden` 列表、原 import/ImportFrom 检查、`open/hash/eval/exec` 调用禁令和最终 violations 断言均未删除或降低。W007–W009 的既有例外保持原条件。
2. 新增例外要求目录为 normalization、语法为显式 `ImportFrom`，并同时限定具体文件、完整 module 和符号集合。`local_connectivity.py` 只允许从 `state.local_connectivity` 引入 `DRAFT_TYPES`、`LocalConnectivityDraft` 和 `build_local_connectivity_draft`；codec 只允许对应 registry/draft 和 `state.regions.EffectiveDraft`。没有允许 `state` 整包、mutation、repository 或 transactions，也没有给其他 normalization 文件相同权限。
3. 实际被允许的 `LocalConnectivityDraft` 是 frozen 中立草稿，`DRAFT_TYPES` 为闭合类型 tuple，builder 构造本地只读图；此次仅为架构 §11.3 所属纯构建/DTO composition 建立与 W008/W009 同类的窄例外。最终代码 review 仍须独立核验所有实现行为，不能以白名单名称代替纯度证明。
4. 新增 W010 守卫覆盖 `domain/local_connectivity.py` 和 `state/local_connectivity.py`：两者均禁止 normalization、importers、pipeline、repository、transactions、legacy、tests 与列出的 IO 模块，并禁止直接 `open/hash/eval/exec`；domain 另禁止 state 和 tech。state 使用纯 tech metadata/schema 不被误判成捕获认证或 parser 依赖，符合 §11.2/11.3 的方向。

## 独立检查与限制

- 读取实际 diff、完整原守卫/新增守卫及被例外引用的模块声明，回查架构原文。架构文件 SHA-256 为 `0a3ca52fed12af500d973deb3bddebac9a8f7f8f697769dc86827a59c07196c9`。
- 用标准库 Python AST 在内存提取并执行新增 `allowed_local_contact_state` 表达式，13个 synthetic import controls 全部符合：4个声明的纯引用被允许；9个 mutation/未知符号/混入未知符号/repository/transactions/其他文件/codec调用builder/普通整模块import 对照均不获此例外。没有写入或修改任何被测源码。
- 读取执行者提供的定向日志：[Python3.10](pytest-310.txt) 为 `2 passed in 0.29s`，[Python3.12](pytest-312.txt) 为 `2 passed in 0.27s`。这些是执行者实际测试结果，本 reviewer 没有将其冒记为独立重跑。

此类 AST 守卫是显式依赖/调用回归检查，不是任意 Python 动态行为、全部传递依赖或 mutable publication 行为的形式证明。原运行时合同及最终独立代码 review、完整双解释器工程矩阵仍需保留。本轮唯一写入为本报告；未改代码、tests、任务、current-work，未提交或推送。
