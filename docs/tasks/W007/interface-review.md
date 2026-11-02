# W007 独立接口 review

Reviewer：`/root/interface_review`；未参与方案设计或产品实现。2026-11-02。基线与 HEAD：`64b4ad2f77c017affade69374510dc12e534bc07`，分支 `codex/w007-semantic-identity-normalization`。受审方案为 [interface-plan.md](interface-plan.md)，初次 SHA-256：`1fb44f82300a5483b6c957afd9ffc680ad8ec61268e5a861d5b04c5f9a353348`。本记录不是产品代码 review 或 PM 验收。

已读根 AGENTS、README、协作/环境规则、W007 A1–A7、架构 §1.4/2.2–2.3/3.2–3.3/5.3–5.4/7.1/11.2/11.10/11.13–11.15、W003 合同、W005 拆分与 reader/evidence、W006 接口及中立 DTO/codec。核对所选 physical/formats profile 和实际 query/header/closure。目录下无局部 AGENTS。

## Findings

| ID | 等级 | 原问题、依据及影响 | 必需处理 | 状态 |
| --- | --- | --- | --- | --- |
| IR-01 | 必须修正（方案澄清） | 方案要求 header 的 URI/closure 与 captured sources 一致，但未区分声明 URI 与 W005 已解析的 SourceFile URI。`importers/reader.py::_binding` 比较捕获时解析路径，合法 symlink alias 不必出现在 `ParseResult.sources`；若新适配按 URI 字面 join，会拒绝 W005 已支持成功输入；若按 hash 随意查找另一 role，又掩盖拼装。W007 行为 1/A1/A6 要求只用已捕获事实并保持 W005 行为。 | 明确 role 由 completed kind 与其 refs 确定，声明 hash 核对该 role 的 captured source；原声明 URI 原样保留，不重读/resolve，也不凭 hash 在 source/target 等 role 之间选择。明确此处信任 W005 成功解析事实，只验证现有 receipt 的内容/来源/跨记录一致性，不声称从 SourceFile 重新证明完整历史路径映射。加实际 alias 成功与不同内容混源拒绝回归。 | 已在方案复核关闭；见下文 |
| IR-02 | 必须修正（方案澄清） | 方案列出 frozen typed DTO 和 wire validation，但未明确聚合 DTO 的跨引用守卫。仅验证 ID 类型/单记录字段，会允许外 cell DeviceId、丢失或重复 net membership、seed 携同类型但不同 query key、delta operand 与 before/after 不对应等组合被标为 success。依据 W007 行为 2/4/5/7 及 A6。 | 补充聚合 constructor/decode 的引用一致性要求：typed ID 唯一且 cell scope 匹配，terminal↔net membership 完整一致，identity/seed 指向该 source 的正确对象和 query key，differences 的 operand/scope/before-after/provenance 与本次 source/target 对应；相关 invalid 组合测试。 | 已在方案复核关闭；见下文 |

## 独立检查与结果

方案已完整保留 source/target、所有参数轴、所有 top、完整 differences、query seeds 的职责划分；没有以 resize=false 丢弃目标，也没有提前发布 baseline/no_change/terminal。C08/C09/C10 的分类与原 fixture 意义一致；C13 channel_length 变化归后续 planner 的义务明确。模型名称来自 profile，端子/轴映射没有靠命名猜测。预期 error 与 unexpected exception/interrupt 边界、双解释器/包验证、独立代码 review 均已列入计划。

IR-01 反例实际执行于 Linux、`/workspace/.venvs/layauto/bin/python -B`（3.12.14）：用 `tests/contracts/w005_cases.copy_input` 复制 fixture，在副本创建 `source-alias.cdl -> source.cdl`，只把 `query/header.json.source_netlist.uri` 改成 `source-alias.cdl`，再调用 `read_inputs(site_config.yaml)`。结果：`success []`；header URI 为 alias；CDL captured URI 是 `source.cdl`；sources 没有 alias。该检查没有改已验收 fixture，临时目录已清理。

源码/包尚未实施，本次未执行 W007 功能、typing/build 或完整回归；不能以接口 review 代替这些证据。两项均可在既定合同内修正，不需新的用户审批。

## 修正复核

执行者随后修正方案；复核版本 SHA-256 为 `ffd0405bb0481987c7a3e55f23d3d122eeb5d2d413884f3dbd429e6cf08e0417`。Reviewer 重新读取全文，确认 IR-01 已明确按 evidence role 先定来源、核对声明 hash、保留 alias、禁止跨角色 hash 查找及历史路径信任边界，并追加真实 alias/混源回归要求；IR-02 已补聚合 DTO 的跨引用、membership、seed 和 diff 守卫及非法组合验证要求。两项方案 finding 关闭，剩余必须修正项 0。

结论：可按现有 W007 范围进入实现；这只表示内部接口方案满足已审要求。实际实现是否落实来源校验、聚合守卫和 A1–A7，仍须最终独立代码 review 与真实测试核对。无需改变输入解释、profile 能力、xref 容错或失败阶段。

## FR3 捕获请求文档锚定补审

2026-11-02，reviewer `/root/interface_review`。本次只审接口修订，不参与修复实现；产品候选 HEAD 为 `6712cbcf0e00395a32836122639c79a88c3813b6`。受审 [interface-plan.md](interface-plan.md) 含末节“FR3 捕获请求文档锚定方案”的 SHA-256：`932fb9be81d3e035270bf21615848ee63e710de55ac3741f417f55bfc61590e9`。独立代码 reviewer 的 CR-01/FR3 及实际反例见 [code-review.md](code-review.md)，该 finding 不因本次方案通过而关闭。

重新核对架构 §2.2–2.3、§5.3–5.4、§11.2/11.10/11.13–11.15 与 W007 行为1/7、A1/A3/A6，并读取现有 `importers/config.py`、`domain/_normalization_input.py` 的 request/response 检查及代码 review 原文。`load_document(SourceFile)` 使用传入的 immutable bytes，源码没有 filesystem read/resolve；`validate_document` 调用现有 closed schema。其已验收 YAML/Unicode 处理比新增仅支持 JSON 的私有解析路径更能保持现有输入解释。

**结论：本次接口修订通过；剩余必须修正项 0，可在既定范围实施，无需新增用户审批。** 原方案“normalization 不 import importers”是本任务内部自选限制；架构明文禁止 domain 依赖 importer，却没有禁止 normalization 调用已有的纯内存格式解码函数。用户要求禁止重新读取磁盘或另读一份输入；对来源已绑定的同一 `SourceFile.data` 做一致性验证不新增事实源。将 W007 专属 input/result/validation/codec 移到 normalization，并保持 domain 的语义类型和 ID 纯净，能满足该依赖方向。它没有改变输入解释、profile 能力、xref 容错、组件失败阶段或 W005/W006 协议。

实施和最终复核仍须兑现以下原要求：

- 许可依赖仅限 `normalization._validation` 调用现有 `importers.config.load_document/validate_document`；传递 selected profile 的 text byte/depth 上限，不改 schema，不调用 reader、acquisition、Path resolve 或磁盘读取。原 domain 入口删除后不能留反向 re-export，所有 domain imports 须继续符合架构。
- 捕获的 requests 文档是 request index、object/path/capability/record_ids/command_intent 的锚；metadata 顺序和 field_sources 自身都不能独立授权关联。须核对每个请求、每个 polygon ordinal 及 capture，禁止漏项、重复项及成组交换绕过。
- 公共 constructor、factory 和 wire decode 使用同一校验。该纯 decoder 遇非法拼装 capture 的预期 `InputError` 应在 DTO 边界转换为既有 `ValueError`；不得扩大 catch 范围吞掉意外 Exception 或 KeyboardInterrupt/SystemExit。真实合法 W005 输入继续进入组件准入，而非被新增校验错误提前拒绝。
- JSON/YAML、合法 Unicode escape、合法请求重排、FR3 完整交换反例、无 IO、domain 依赖方向及 W005/W006 回归需在修后新版本实测。`6712cbc` 的候选证据只能保留为历史，不能冒记为修后 A7 或 CR-01 的关闭依据。

本次未运行尚未实施的修复测试、typing/build 或包验证；最终实现、实际效果和 CR-01/FR3 关闭仍由独立代码 reviewer 依据修复提交与证据核验。本段不是 PM 验收。
