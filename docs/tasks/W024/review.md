# W024 独立复核

## 方案复核

**可以按方案实施。** 复核发生在产品修改前，基线为 `11506059006f7fb377732b4d0287e1f4fd72e057`，所审方案的 SHA-256 为 `cb7b5c82263ad59919b8ea2975b59d3ec6c9ccc7eaef3c121e8e050537d5c0a6`。[方案](plan.md) · [A1–A5](../W024-stage3-rule-context.md)

| 发现 | 复核依据与实施要求 |
| --- | --- |
| P1 工艺允许两条间距规则互换 evaluator | 在 Python 3.12.14 取原始规则，用 `tech.schema.validate_payload(freeze_map(doc), 'rules')` 单独改变第 7 行。T07 换为合法 T06 evaluator、改作用范围为仅已标注 M1，两次均通过上游校验。检查器要匹配 ID、确切 evaluator、范围和选中算子，对不能解释的组合给出来源字段和 indeterminate。正常的变阈值样张应让结构参数和文字描述一致。 |
| P2 失败的归属 | 同一探针把 evaluator 改为 `unavailable/2`，收到 `UnsupportedRuleVariant /rules/6/exact_evaluator_ref`。把关系改成 `same_component`，收到 `RuleDeclarationConflict /rules/6`。应复用上游拒绝。对能封存但缺检查能力的数据和实际 evaluator 异常，按所选 policy 的两种处置分别验证。 |
| P3 复用的两个身份 | W023 `seal_context` 先验证旧 snapshot 和本次输入的绑定相同，再把本次 checkpoint 与旧 head 放进新的 context。读入口应沿本次 attempt 持有的 context 找原快照，再从本次封存证据解析工艺；独立呈现检查 run 与创建版本的 run。 |
| P4 单位与见证 | `DrawnRecord.rect` 使用 canonical DBU；见证应定位两条带源 SHA 的 GDS 记录。距离平方乘 `canonical_tick_nm²` 后才能与 nm² 阈值比较。重叠和正长共边用既有接触算子处理，单点仍是零距离的可判定一对。 |

P1、P2 的探针只读所选规则原件。P3、P4 核查了基线上 `repository/publication.py`、`domain/geometry.py` 与 `state/local_connectivity.py` 的实际实现。代码复核将按交付提交核对这些约束并独立读取 GDS 字节。
