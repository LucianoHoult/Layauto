# W013 交接范围与验收映射专项核对

核对者 `/root/oracle_audit`，2026-11-12；未参与方案设计或实现。早期只读调查了真实
tech/query、独立 oracle、W003 人工决定与 legacy 边界。本次只读检查实际方案、六个新
runtime 模块、测试和独立 review 证据，不替代最终工程身份审查、完整代码 review 或 PM 验收。

## 受审身份与范围

本次核对 HEAD 为 `2a45938aba8e751183d472d660a1ab66a1063636`，分支仍为
`codex/w013-net-annotation-coverage`。逐项读取并计算
[R2 冻结清单](verification-r2/source-manifest.json) 的 273 项实际源码/测试/config 文件
SHA-256，全部与当前工作区相同，0 项差异；完整 source_id 为
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。
这里没有用 HEAD 或测试数量替代实际文件身份。

相对 PM 准备起点 `d6182fe6893c26490f9d58c6b808a5ce9910384b`，实际产品范围为：

- 新增 `domain/net_annotation.py`、`state/annotation.py`、`annotation/net_regions.py`、
  `derive/net_annotation.py`、`normalization/net_annotation.py` 与
  `normalization/net_annotation_codec.py` 六模块；修改 normalization 公开入口和 typing 清单。
- 新增三个收集测试文件 `test_w013_net_annotation.py`、`test_w013_contracts.py`、
  `test_w013_composition.py`，以及一个共享手算/临时 capture helper `w013_cases.py`。
  因此“四个新测试文件”包含该 helper，不表示四个 pytest 收集模块。
- R2 另有保留 `test_w007_contracts.py` 的精确只读 `AnnotationDraft` 导入白名单维护。
  独立 [code-review](code-review.md#保留边界guard失败与r2资源身份采信复核2026-11-12)
  保存其原因与复核；原首轮失败不改写为通过。
- `git diff --name-only d6182fe... -- tests/fixtures docs/architecture.md docs/roadmap.md
  docs/current-work.md` 及旧 semantic/effective/local/channel codec 检查均为空。
  无 baseline fixture/答案、旧 codec、架构、roadmap 或 current-work 修改。

## A1–A8 覆盖映射

| 要求 | 具体实现与判据 | 当前专项判断 |
| --- | --- | --- |
| A1 同源与身份 | [方案](interface-plan.md) 的同源 W010→retained W007 输入；normalization Result 完整旧 public codec 认证并重新 normalize；neutral binding/owner/source 闭合。contracts 覆盖 source 缺失/替换、跨 query-run/database、跨有效 readback receipt、伪造输出与 007 拒绝 | 当前捕获子集有明确实现和测试；007 按用户选项 A 保留拒绝，不宣称支持 |
| A2 精确区域 | annotation 模块用 Fraction 精确交集、difference、分片；state 验证所有 target/match/fragment 完整重建。unit/composition 覆盖部分交叠、同网重叠去重、边/点零面积、1/20nm、小孔/分离片、CUT trim 与 unmatched 分开、同 cell duplicate records | 正常合法 exact 数据进入成功 overlay；没有 query 造几何、中心整格覆盖或按名字猜网 |
| A3 分量摘要 | derive 模块逐原 component 收集直接 evidence；composition 核完整本地图、独立成员映射、同 component 不重叠不同 net 冲突、cut 两岛加主 A 分量 | 不按 semantic net 合并物理组件，不改边；region direct coverage 与 component 关联明确分开 |
| A4 缺口与质量 | matches 保留 unmatched/trim/boundary/multiple-candidate；fragment unknown、per-layer coverage 和全 drawn classification。测试核 marker、BODY/OD direct unknown、partial、冲突面积与非零 tolerance unsupported；非 exact seed 在现行上游拒绝 | 不把缺口自动等同整轮成功/失败；unknown 不提供任意 net 兼容结论；不升级 approximate 质量 |
| A5 DTO/公开边界 | domain/state 完整中立校验；新 codec closed/versioned canonical，完整旧 W010 Value 一次承载并重新认证；contracts 覆盖 native scalar、nested aliases、field completeness、跨进程 ref、完整输出篡改、原异常 object/cause/context/suppression | CR-01 operator owner、CR-02 writable backing、CR-03 分类/contributor 原失败和修正复核均保留，独立必须项已关闭 |
| A6 作用域与有效性 | binding 固定 `source_evidence_local_net_annotation/1`/`source_evidence`；public Result 来自当前完整 input。composition 禁 IO/发布、readback attempt 不推进、terminal 为空，并保留 body evidence 对象 | 仅 local source-evidence draft；无 baseline/terminal/新 LVS 或完整 M1/真实 EDA 保证 |
| A7 成本节点 | 方案有调用/序列化展开及 1/1/2 public decode 计划；resource02/03/04 保存首完整及修后 direct/readback/mismatch，资源分析和独立审查说明旧 input/new compact 成本及 retained roots | 已有资源专项核验；R2 只读 test delta 采信 resource04，原 source_id 不回写；本专项不重复 capture |
| A8 工程与独立 review | 方案独立实施门、CR-01–03 原失败与复核、75 新项/110 受影响项开发记录、R2 新冻结双 1731 collection，以及最终 runner/证据专项审查 | 本次核对时 R2 最终矩阵/typing/build/双干净安装源码外 smoke 尚未有全部完成证据，不能提前标 A8 或 A1–A8 全完成 |

上表是范围与证据入口映射，不将测试存在或 reviewer 必须项0当成尚未完成的实跑结果。

## 独立本地 oracle 与使用预期

当前 `oracle.json`、`independent-design-answer.json.local_scope` 和 fixture README 均明确
14 本地有效导体区域、8 条 connector 边、6 个分量；外部 context 不属于本地图。
`test_actual_direct_result_keeps_complete_local_graph_and_independent_net_projection` 核实际
node/edge/component 全集合，并与 `w013_cases.LOCAL_COMPONENTS` 的独立成员答案逐项比较：

- ON.S/LN/MN→VSS；OP.S/LP/MP→VDD；ON.D/OP.D/LY/MY→Y；G/MA→A。
- BN、BP 分别独立，本地 net unknown；外部 body rail association 不补本地边或直接标签。
- 直接 query 只有 G、LN/LP/LY、MN/MP/MA/MY 八 targets。POLY720 + LI1110 + M1 1340
  =3170nm²；全部14 target 分母35090nm²，未直接覆盖31920nm²。
  四个 OD 端子虽可读 component 关联，仍不冒充直接 query 覆盖。
- MARK=`[145,180,150,185]`、面积25nm²，完整保留并分类为未注释 marker，不计导体分母。
- CUT 测试只改临时输入副本并重绑真实 capture，保留左右各36nm²、CUT gap8nm²和外越界
  unmatched8nm²。其 A 主分量与两孤岛仍为三个物理组件，未改原 standalone fixture。
- 重复 M1 occupants 仍分别计入 target multiset 分母；同 target 重叠 query 只累计 union 面积。

上述与 MR-020 孤岛拆分、MR-022.1 MARK 保留、MR-033.1 R00–R07 对应、MR-052 人为桶
范围一致。旧16节点/10边或把孤岛加回正常例的旧建议未冒充当前正常答案。

[P01 决定](pm-decision.md#p01-用户决定2026-11-12执行按原答复记录) 明确采用用户选项 A：
保持当前实际 ordinal 捕获，007 为不支持/拒绝反例。contracts 同时核真实1/2/3/4字符串、
QueryKey 007 原拒绝和完整 captured NET NAMES 伪造拒绝；没有为了满足旧词法扩展 parser。

## 最终交接需要补记的内容

本次未发现新的产品/合同必须项。任务执行区当前保留的恢复点仍写 resource04 复测前与
旧 source `6463eb67...`；最终交接应追加最新 R2 source、精确 test-only delta、首轮失败
保留位置及最终所有实跑回执，不回写历史段或 PM 阶段。

最终 A1–A8 完成判断仍须等 R2 双全量/typing/build/双 fresh 安装源码外组合 smoke 和
独立工程身份/完整 review 结论闭合。之后沿用原分支提交推送、核远端完整 SHA 交 PM；
不代 PM 验收、合 main、更新 current-work 或启动下一任务。

| 分工 | 本专项事实 |
| --- | --- |
| 本次实跑 | 只读源码/测试/方案/review 映射检查、273项当前字节与 R2 manifest 比对、限定禁改路径 Git diff 检查 |
| 按身份采信 | 原方案门、CR 修后探针、开发/资源回执；其最终身份与原日志的全面核验由独立证据 reviewer 负责 |
| 未覆盖 | 不重复产品 capture/full/typing/build/install/smoke；不为运行中的最终矩阵提前作成功结论；真实 EDA/生产规则等既有非目标仍未覆盖 |
| 补跑触发 | 实际源码/测试/config/输入/依赖变化、证据缺失或身份不闭合、新风险；仅此文档专项附件不触发重新双全量 |
