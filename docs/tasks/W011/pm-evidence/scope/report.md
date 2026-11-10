# W011 PM 接收：范围、算法与上游增量核对

检查者 `/root/w011_pm_scope`，2026-11-10 UTC。被审起点 `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`，交付/本机 HEAD `3c464baade7b6ea8c712cfb84265490b8e3f754e`；产品修正为 `8917d38d916c914bfa785cb116982f3f299b38de`，执行最终冻结为 `e89bdaa6a091f56cfaf7862dced7232d34e22514`。

**本专项新增必须修正项 0。** 本结论是 PM 接收辅助，不代替用户要求的专门 premerge session 或最终 PM 验收。

## 方法和实际运行

读取根 AGENTS/协作规则、W011 要求与 plan/plan-review/code-review、相关架构 §4.5/5.6/11.5/11.9；检查 10 个产品路径的实际 diff，重点检查 annotation/derive/new result/codec 及上游 source_location、normalization codec/component 改动。结合正式测试的断言检查覆盖，没有运行完整 pytest、captured result build/readback/codec、安装、EDA 或资源 probe。

- `static-result.json`：保存 HEAD、10 个产品路径 SHA-256、AST imports；未发现 legacy/tests runtime import。81e01da→交付的 fixed fixture、tests/support、architecture、current-work 和 roadmap 均无改动。
- `coverage_probe.py`：本专项新编的轻量 exact rational union 独立检查，256 个确定性 case、5,981 个 open-atom membership 对照通过；同时验证 cover 不重叠、精确面积、输入顺序不变和幂等。0.129s，使用已有 Python 3.12 环境、禁 bytecode；`coverage-result.json` 保存脚本 SHA/版本/结果，stderr 为空。此 probe 不使用 fixture/oracle，也不证明捕获身份或完整组件组合。

## A1–A7 与关键语义

| 要求 | 代码及实际边界判断 |
| --- | --- |
| A1 同源组合 | `normalization/channel_identity.py` 只有一个成功 W010 result 输入；先 closed graph 再完整 W010 codec 重建，随后用保留的 GeometryInput.semantic_input 调 W007 normalize。caller 无法另传一个 semantic result。derived payload 与原 tech.sources[2] 绑定；completed 同时检查对象相等和 canonical bytes。 |
| A2 正常有限计量 | derive 遍历 channel×全部 FIN，实际 count 独立计算，source 比较使用关联成立的 DeviceId；G/S/D 从既有 region/node/component 回链。正式测试核完整 crossing 集合、18 FIN、共享 G 和四个 S/D；本次未重跑该重型组合。 |
| A3 FIN 精确性/重复 | evaluate_fins 先按正面积，边角 touch 不计；qualified 需要完整 channel X 和 active Y。跨不同 X channel 可分别计。重复/重叠关系保留两个记录及交集，只对涉及正面积候选的 channel 将 count 设 None 并发出 UnprovenIndependentFins；范围外重复保留但不毒化其它 channel。没有选定“重复一定算 1/2”的新物理解释。partial crossing 保留诊断及可判 L/W。 |
| A4 seed 定位/coverage | locate_channels 保存每 seed 的全部正面积交集，不能用其它 seed 消掉自身多解。唯一定位后按 DeviceId 聚合，核全部 source devices/channel 的一对一；coverage 使用 Fraction exact union。partial 唯一 seed 可定位，但明确不是完整区域 annotation；没有新增 full-cover 准入门槛。缺 identity 时 channel 几何 measurement 仍保留，只有有效关联才生成 source 参数比较。独立 rational cover probe 补核本算法。 |
| A5 source/target | 纯 derive 输入只包括 local/source/seeds/derived，没有 target 数值作为计量输入。每个 count、channel 长度和所有正面积 FIN 实际宽度比较都保留；完整 differences 从所有 mismatch 派生。target 仅保留在单独的 W007 semantic result。0 crossing 的宽度未测有 coverage 字段，comparison_status 不会因空 width 列表变成 equal。 |
| A6 公开合同/异常 | 新叶及 aggregate 按确切类型重构，Result 对 supplied draft 调完整 replace 再用完整 codec 表示比较，补全早期只比摘要漏未测来源的问题；completed 用 typed canonical equality。codec 无 broad catch。expected ChannelProblem 和 W007 NormalizationError 后都在 except 外构造/再认证，保留意外异常的原历史。 |
| A7 scope | Result 完整保留 W010 graph/T05 audits 和 body evidence；derive 仅引用 topology，不写边/union。coverage 明列 complete net/body/model/VT、T02/all mandatory、manufacturing coordinates、U06 和 publication/no_change/Stage6 deferred。没有把有限 equal 提升为完整 extraction equality。 |

## 原 findings 与小范围上游改动

- CR-01：ChannelSeed 验证 closed fields、opaque tuple、完整 field derivation/source operand、xref/common row 与 exact vertices；不只核 key 集合。`source_location.ref_from_location` 新增 FrozenMap 守卫和缺 hash 明确 ValueError；非法 UTF-8 文本也给明确 ValueError，不放任 KeyError/UnicodeEncodeError 泄漏。
- CR-02：`normalization/codec.py` 移除吞掉 TypeError/KeyError/AttributeError/UnicodeError 的 blanket translation，使新 semantic_record→Parameter 路线保留故障对象。原记录形状验证和 canonical pack 比较继续保留。独立原 report 的 384 个字段/类型控制是历史 evidence，本专项没有冒称重跑它们。
- CR-03：`normalization/component.py` 把 facts=replace 和 error Result 构造移出 NormalizationError except；正常 success 路径不变。确实处理到“已捕获预期错误后二次构造又失败”的污染原因。
- CR-04：新类型递归重构、Result 的 full draft replace/encode 比较以及 completed canonical 比较均在最终代码存在；不是仅依赖 Python bool/int/Fraction equality。
- CR-05：seed_source 解包 sources[0]，Missing/AmbiguousSeedChannel 保留该 source pointer，message 加实际 record ID；不再覆盖为不存在的 operator pointer。原 wrapper 和 pointer 两段关闭在 review 保留。
- CR-06：derived registry operand 的 canonical lexeme、实际 URI/SHA/JSON pointer 与传入 owner 的同位置声明交叉比较，拒绝内部矛盾；捕获真实性仍归 normalization，未在纯 derive 引入 IO。

上述处置与 reviewer 最终 8917d38 复核记录一致。没有发现这些必要上游修补扩大输入格式/能力或改变 source-target 含义的证据。

## 建议 PM 的短回归

统一选择 geometry 和 contracts 模块中的：

`-k 'normal_result_matches_all_independent_crossings or exact_fin_geometry_against_independent_open_atom_witnesses or all_topology_refs'`

geometry 的 module-scope accepted 只构造一次完整 W011，之后 exact FIN 边界与集合核对多为中立计算；contracts 的独立 accepted 会再构造一次，若需控制在约两分钟内可先只选 geometry 两组。预计小于完整 Result readback/roundtrip 组合成本，但执行时间受环境影响；本专项未实跑此选择，不保证精确时长。

## 限制

本次实跑只有轻量 rational cover probe 和静态范围/import 审计。没有重跑正常/mismatch/readback 捕获组合、全部异常矩阵、typing、双解释器、构建/安装或峰值资源观测；这些证据由 PM 的其它专项/原 review 核验。本专项 0 项不等于完整 premerge review 或集成验证完成。
