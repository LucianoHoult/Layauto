# W004 修订版样本导航（保留W003路径）

先核对小单元的几何和连接，再检查文件链是否保真。`INV_M1_SYNTH` 的 source/target 都是 N=5、P=7；预期没有 ECO commit，但仍须检查全部 toy 规则并导出一致文件。

本目录是 [W003](../W003-m1-fixture-contracts.md) 的执行附件，产品合同仍以 [architecture](../../architecture.md) 为准。这里的 schema 和字段拼写为 `w003-example/1` 审查用样张，尚未经 PM 接收为产品 wire API。所有 run、snapshot、check、报告均是**预期样张，未执行产品 run**；辅助检查的实测结果另存执行证据。

![正常本地几何、外部body支持与独立CUT专例坐标图](fixture-layout.png)

图从手写 spec 绘制，仅辅助人读；正确性来自逐坐标/端子表与独立 reader，图不是另一个 oracle。前两面板为40图形正常例；第三面板为不导出的只读外部tapcell上下文；第四面板为独立CUT/同标签/同格专例。图域分列，不将外部支持画成本地物理边。

| 入口 | 用途 |
| --- | --- |
| [W004执行记录](../W004-fixture-revision.md#w004-execution) | D1–D3正式派发、R1–R5/V1–V7覆盖、完整版本与新版独立review入口 |
| [单位/尺寸/owner来源](../../../tests/fixtures/w003_m1/sources.json) | 所有本地尺寸、设计选值、规则适用条件、来源与缺项 |
| [W004原始交付封包与校验](delivery/w004-20261031/) | 已审版本的完整snapshot/binary patch、命令环境输出、独立审计及原SHA-256；保留原包bytes |
| [新版迁移与验证](revision-evidence.md) | 原22目的及新增body见证、8失败记录、未运行项和人工待闭合 |
| [人工核验清单](manual-verification.md) | 用户答复、修改要求及最新恢复点；本轮收尾汇总见MR-076，持续进度以本清单为准 |
| [网页 Codex 交接](web-codex-handoff.md) | 最新mental checkpoint、历史角色与接续prompt；2026-10-30转修订交接，不替代清单或产品合同 |
| [文件与记录合同](contracts.md) | M1 producer/consumer、exact encoding、必需字段、非法组合和失败流 |
| [记录样张](examples/records.json) | Evidence、attempt、baseline、snapshot、RunRecord、Manifest/check/report/terminal 的相互引用 |
| [失败样张](examples/failures.json) | pre-context、sealed、freeze、export/check/report/terminal 的代表组合 |
| [人读报告样张](examples/report.expected.md) | 工程 no_change 应如何披露结果和缺项 |
| [schema 字段表](examples/schema.json) | 样张专用 closed record 字段/variant；不是产品 parser |
| [后续实施与 PM 接收](handoff.md) | 要求覆盖、legacy 取用、真实缺项、首交错误路径和复查步骤 |
| [synthetic 输入](../../../tests/fixtures/w003_m1/) | 手写 spec/oracle、GDS/CDL、raw/header/normalized、toy tech/site/policy 和失败输入 |

样本内部可以使用明确声明的 toy 单位、模型和语法；这些选择不表示实际 Calibre dialect 或保密 PDK 已确认。生产回传权限、平台 build、离线依赖和真实验收回执仍交 PM 协调，不阻塞本地准备。
