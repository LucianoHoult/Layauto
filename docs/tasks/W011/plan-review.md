# W011 独立方案 review

Reviewer：`/root/plan_review`，2026-11-09。未参与方案调查、设计或实现；只写本报告。

**结论：必须修正项 0，方案可进入实现。** 这是执行方案 review，不是代码 review、A1–A8 实测通过或 PM 验收。

## 受审身份与读取范围

- 仓库 `/workspace/Layauto`，分支 `codex/w011-channel-identity-fin-count`，HEAD `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`。
- 受审未提交方案：[plan.md](plan.md)，SHA-256 `24a4d3b4c1f95851f35f77a0e6744af3c6618590741976882e7e2010ae38e94e`。开始时它是唯一未跟踪文件，无产品改动。
- 已读根 AGENTS、README、协作规则、current-work 的 W011 入口、[任务正文](../W011-channel-identity-fin-count.md)，并搜索 docs/layauto_v2/tests 无局部 AGENTS。
- 直接对照架构 §1.4、§4.5–4.6、§5.3–5.9、§11.2/11.5/11.9/11.15，W003 contracts、MR-008/009、MR-031/032.1，实际 physical/derived owner 与正常几何表。
- 核对 W007 NormalizationInput/Result/seed、W008/W009 捕获保留、W009 channel/terminal/重复 POLY、W010 公共结果/完整重建及 node/component/audit 合同。读取既有实现是接口可达性核查，不替代未来新实现的实测。

## A1–A8 覆盖判断

| 要求 | 方案判断与依据 |
| --- | --- |
| A1 同源组合 | 唯一输入为成功的 W010 结果，先检查原对象的 closed graph，再完整 codec 重建；从其 GeometryInput.semantic_input 运行 W007，而不是接收独立可拼装语义结果。中立算法和 normalization 捕获认证职责分开。保留 direct/readback、完整输入和 unsealed attempt，并计划禁 IO 负例。 |
| A2 正常结果与回链 | 逐 channel/FIN 枚举，完整集合对应 MR-008/009 的 5/7 和 18 drawn records；L/W 来自 geometry。S/D 用 W009 region 回链，G 使用所有 POLY contributors，因此正常两个 channel 可以共享 G，也不意外拒绝 W009 已支持的相同 stripe 多 POLY records。 |
| A3 几何边界 | qualification 与实际 physical owner 一致：先正面积，再完整 channel X 跨越及 active Y 包含，允许等号。保留 touch/outside/partial，不按面积、Y 或 query 高度计数。长 FIN 跨不同 X channel、精确有理和大整数均有计划。重复/重叠示例不假定 1/2 根的新答案，按不能证明独立物理 FIN 的既有 unsupported 边界处理；不触及 channel 的记录仍保留。 |
| A4 定位/覆盖 | 表格明确 full、2/5 partial、跨两 channel、同身份多份 seed、零面积与 5/8 有理 coverage。先逐 seed 完整候选，再核 source devices↔channels 一对一；不通过排序或其它 seed 消除某 seed 自身的多解。联合 coverage 使用 exact union，不重复加重叠面积。唯一定位不冒称完整区域 annotation。 |
| A5 source/target | 现有 ON.y1=64 的失败输入将 F05 判为零面积触边，得到实际 4 对 source 5。source count/L/逐 FIN W 比较保留全部可判差异；target 与全部 target differences 单独保留，NF/M 准入不冒充独立几何测量。成功计量可携带明确 mismatch。 |
| A6 公共合同 | 新 domain 值类型与 derive aggregate 不依赖 normalization；结果构造和 decode 重新生成完整表并比较，不只核 count 或引用存在。显式一次 collection snapshot、closed graph、canonical wire/digest、跨源与假一致拒绝、expected 后二次认证的异常链保真均在计划中。 |
| A7 scope | 保留原图、完整 T05 audits、外部 body evidence 与未消费声明；只消费所声明的 FIN/seed 解释。没有 net labels/新边、S-D union、body 合并、model/VT 验证或完整规则通过。T02、U06 与发布闭环继续后置。 |
| A8 工程与交付 | 原1465 node IDs、双完整解释器、strict typing、构建/双干净安装、源码外真实 direct/readback、身份清单/完整快照、原命令输出及独立代码 review 均覆盖；披露枚举和重复捕获认证成本、wire/RSS及未测上限，不把样本性能当最大输入保证。 |

## Findings 与实现核验提示

必须修正 findings：**无**。未修改方案或提出新的输入解释、能力或用户决策门。

以下为非阻塞核验提示，落实任务已有“全部可判差异”和“诚实 scope”，不改变上述结论：

- **PR-N01（P3）**：当 count 因 partial/重复独立性未知而为 None 时，已能独立求得且有有效 device 关联的 L/W 比较仍应保留；不要因一个未知轴抹掉其它可判差异。零 qualified crossing 时没有逐根 W 实测，不应将空比较集合汇总成“W 已验证一致”。代码 review 应专门核对这些不完整计量结果的 summary。
- **PR-N02（P3）**：完整结果将同时保留 W010 receipt 和 W007 semantic result，后者也含捕获。记录资源时须测完整公开 result wire/constructor/decode，不能以中立 draft 的小体积代替它；两条路径的资源分别披露。方案已列出这个成本，提醒最终证据准确对应对象。

## 实际检查与限制

本次实际执行 git status/rev-parse、sha256sum、rg/sed/cat 阅读以及 Python 标准库读取 spec 几何条目；核对 F01/F05/F07/F13、ON/OP/G 坐标与手工表。未运行产品测试、生成器、包构建、安装、EDA 或完整性能测试，未声称实现已满足方案。

未改任务要求/阶段、current-work、main、架构、fixture/答案或代码；未提交推送。后续若改动方案的关键输入解释/公开合同，需复核相应增量。实现完成后仍须由未承担实现者独立代码 review，PM 按最终身份及 A1–A8 实证接收。
