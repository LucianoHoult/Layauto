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
