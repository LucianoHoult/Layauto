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

## 代码复核

基线为 `11506059006f7fb377732b4d0287e1f4fd72e057`，首次复核与修复复核的实跑、发布 SHA 见下表。本次核对了公开入口、W023 的封存与解引用保证、工艺 owner 的选择、规则能力匹配、几何谓词与结果、模块方向及新增测试。环境为 Linux x86_64、CPython 3.12.14、PyYAML 6.0.3。

GitHub 的提交邮箱隐私检查要求更新提交身份。独立核对了两组 `git show -s --format='%H %T %P'`，逐组运行 `git diff --exit-code 实跑SHA 发布SHA` 均返回 0。复核探针及新增、受影响的 108 项检查按同一完整 tree 采信。

| 材料 | 独立复核实跑 SHA | 对应发布 SHA | 完整 tree |
| --- | --- | --- | --- |
| 首次实现 | `29baffe2985ea01877080a00bff240e706251e1d` | `8c0f2fa3a84cd13996720ff5f9abc787d3901347` | `e49f7094df76608b2c3dffdb8c6097d18f0f66fc` |
| R1 修复 | `54554871c685cd06dae482ce95736ebb079c9c84` | `1828ec860b2bf5be71f56ed91bb9c68a8acc67bd` | `b9b198a2ce086d9d4a0a389a0021a514008b1a5f` |

### R1 可把其他版本的违规归给正常版本

在首次受审实现实际发布正常和 C14 后，取正常上下文的 `version`、`catalog` 和 `physical`，以及 C14 的 `snapshot`，装入普通 `types.SimpleNamespace` 交给公开 `check_m1_spacing`。函数返回正常版本标识 `snapshot:normal:c375a87599d40ed1c8a4e9d85a359261ed1c2091cbefd0fee5b45e332730ebbe`，报告 C14 的 4 nm 违规。同一实例中正常原版的 6 对全部通过。影响是调用方可以拿到版号和图形来源互相矛盾的正式报告。

### 从原始 GDS 复算

探针从 site 及 tech bundle 找到所选 drawn、format、rules 文件，核对输入 header 的 GDS 与 owner 摘要。它逐条解析 GDS 记录头，核对 UNITS 的两个 REAL8 与工艺 nominal 的半 ULP 误差，再由 BOUNDARY、LAYER、DATATYPE、XY、ENDEL 得到 M1 原矩形。对每一对闭区间穷举整数坐标间最短距离。对这两份整数端点矩形，每个坐标方向的最小间距都能在整数位置取得。[独立探针](review_probe.py)

| GDS 两条 BOUNDARY 的字节偏移 | 正常距离平方 nm² | C14 距离平方 nm² |
| --- | ---: | ---: |
| 2352 与 2416 | 8100 | 8100 |
| 2352 与 2480 | 1049 | 1049 |
| 2352 与 2544 | 2249 | 2180 |
| 2416 与 2480 | 2525 | 2525 |
| 2416 与 2544 | 3725 | 3656 |
| 2480 与 2544 | 25 | 16 |

偏移 2352 与 2480 的斜向分量为 5 和 32 nm，最短欧氏距离平方为 1049 nm²。最近两条的记录序号为 191、196。第一条的原矩形为 (50, 90, 75, 98)，第二条在正常原图为 (80, 90, 110, 98)，在 C14 为 (79, 90, 110, 98)。两次规则文件的 SHA-256 均为 `40ce0b76abb28c07ab734734a19d61e1259bc5aee42a8cf2c02fabb9e4457480`，阈值位于 `/rules/6/parameters/min_distance_nm`，等于 5。正常包 6 对均通过，C14 恰有 1 对违规。探针还逐行核对了示例的 10 条声明、JSON Pointer 和各自状态。[正常 GDS](../../../tests/fixtures/w003_m1/source.gds) · [C14 GDS](../../../tests/fixtures/w003_m1/failures/count_correct_rule_wrong/source.gds) · [规则原件](../../../tests/fixtures/w003_m1/tech/rules.json)

在仓库根目录运行下列命令。第一条读已存报告并从原图复算。第二条同时经公开入口重新发布两个临时输入，逐对核验 12 个测量与状态，并从这两个 context 构造 R1 的反例。

```sh
python -B docs/tasks/W024/review_probe.py docs/tasks/W024/evidence.json
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/review_probe.py docs/tasks/W024/evidence.json --published
```

### 修复复核与结论

**R1 已关闭，代码复核通过，提交 PM 验收。** 在 `54554871c685cd06dae482ce95736ebb079c9c84`，同样的两个正式上下文、同样的公开调用与混合对象，实际返回 `TypeError: T07 requires a published ConstraintContext from open_constraint_context`。合法输入仍通过公开入口核对了全部 12 个距离平方及逐对状态，两次查询前后的仓库观测相同。修复范围为公开入口和对应合同测试。[修复提交](https://github.com/LucianoHoult/Layauto/commit/1828ec860b2bf5be71f56ed91bb9c68a8acc67bd)

P1、P2 的处置符合工艺和上游合同。可封存的错配得到带来源的 indeterminate，运行异常使用 error，两种状态均保留已绑定的 policy action。P3 的检查 run、本次采集与创建版引用在复用路径分别保留。P4 的缩放、点接触、共边和非整数根的单元检查，与上表按原始 XY 算出的斜向及线端结果一致。

独立实跑包括两版 R1 探针、修复版两份文件的实际发布、全部 12 对比对，以及对修复版安装后示例 JSON 的原件核对。该 JSON 的 SHA-256 为 `c78b52bfc52dc95af906bc9d87a0576f6935456597df95bd6e6076eec86a077e`，安装用 wheel 的 SHA-256 为 `5608168d7848a0ac365b33f59a51fdb954857d413f4bb7a8a5fd7fb794fbb971`。独立源码探针使用 PyYAML 6.0.3，交付 wheel 示例使用 PyYAML 6.0.4。受审版本的产品树为 `3a52767a555fc821eb9e7d2072b65b7404194035`，测试树为 `4fa0e9de292da5726922172e0c6e10692a12d255`，其余新增和受影响检查按此身份与执行记录采信。W023 发布、上游工艺校验和样本原件在本次 diff 中保持基线身份。产品、工艺、样本、依赖或合并组合有变化时补跑相应探针。其余九条规则的求值及整轮完成判定留待后续阶段。[执行验证与交付证据](verification.md)
