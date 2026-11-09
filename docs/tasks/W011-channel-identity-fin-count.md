# W011 — 沟道身份匹配与 FIN 计数草稿

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W011；将实际沟道与已认证的器件身份关联，从精确 FIN/active/channel 几何计算有效 fin 数，给出与 source CDL 的有限参数核对及可追溯差异 |
| 里程碑 / 依赖 | M1 内的 Stage 2 组件。W005–W010 已验收集成；起点 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8`，W010 集成与组合证据见其 [PM2](W010-local-contact-connectivity.md#pm2-integration-20261106) |
| 授权依据与范围 | 用户 2026-11-09 要求继续推进并说明整体位置。沿用 PM 准备、独立执行 session、独立 review、PM 集成验收的分工；本次先准备任务，不执行产品实现 |
| 当前阶段 / 阻塞 | 可执行；交接要求独立复核必须修正项 0，PM 已接收。没有需要用户立即选择的新产品预期；下列语义边界须在执行方案中给出明确解释，不得猜测 |
| 恢复位置 | 从上述 main 建立 `codex/w011-channel-identity-fin-count`；接手本任务及准备 review 所在的远端提交，核对完整 SHA 和工作区 |
| 允许修改 | 必要中立 DTO/refs/codec、`annotation/` 的有限 device-channel 定位、`derive/` 或其它符合架构 owner 的只读 FIN 计量、`normalization/` 同源组合；必要 tests、typing/build 配置、README 与 W011 附件。具体模块/算法由执行者决定 |
| 非目标 | 不修改已验收 fixture/答案，不启用 resize；不做完整 net overlay、body 外部证明/U06、完整器件模型/VT/端子匹配、全部 T02/T03/T08 或 mandatory rules、完整工艺坐标/region occupancy、可变状态/lineage、baseline/seal/no_change/terminal/Stage 6、真实 EDA/生产适配 |
| 架构依据 | 起点版本的 [architecture](../architecture.md) §1.4、§2.2–2.3、§3.1–3.8、§4.5–4.8、§5.3–5.9、§6.2、§8.1/8.3、§11.2/11.5/11.9/11.14–11.15、§12.3–12.5/12.8；[W003 合同](W003/contracts.md)与 [manual review](W003/manual-verification.md) 的 MR-006–009、MR-031/032.1；W007–W010 的来源、单位、公开结果合同 |
| 分工 | PM 维护要求/阶段/验收；执行者先细化方案并完成必要实现；未承担设计者审方案，未承担实现者审代码，reviewer 自行保存结论。遵守[协作规则](../collaboration/rules.md) |

### 已核对事实与拆分理由

- [physical owner](../../tests/fixtures/w003_m1/tech/physical.json) 明确 `toy_fin_crossing/1`：identity FIN、identity OD，FIN 须完整跨过 channel 的 x 范围且 y 区间完整包含于 active，partial fin 不支持、不能取整；single-finger、one-to-one、no reduction。FIN width/pitch/offset 有具名 toy 来源，不是生产默认。
- [derived owner](../../tests/fixtures/w003_m1/tech/derived.json) 的 device seed 为 exact rectangle、0 tolerance、`recognized_channel_intersection`、`reject_ambiguous`。它提供空间身份线索，不是几何事实或 fin 数来源。
- W010 保留 W009/W008 的完整捕获链，其中 `GeometryInput.semantic_input` 是 W007 的输入，尚不等于已经运行 `normalize` 的语义结果。可在同一捕获上组合语义和几何，不另读文件或拼接其它 run。
- 正常两器件共享完整 POLY G；channel 分别是 `[58,20,62,70]` 与 `[58,110,62,180]` nm。因此 DeviceId 的定位对象是 channel，而非将整条 POLY 归给唯一器件。
- [独立手工答案](../../tests/fixtures/w003_m1/oracle.json)：MN0 为 F01–F05 共 5 根，MP0 为 F07–F13 共 7 根；共 18 根 drawn FIN、12 个合格 crossing，其余 FIN 原样保留。两 channel 长度均 4nm，合格 FIN 宽度均 2nm。测试可按几何回链这些手工名称，runtime 不依赖 spec 的 shape 名称。
- 现有 [extraction_mismatch](../../tests/fixtures/w003_m1/failures/extraction_mismatch/) 将 ON 上边改到 64nm，并同步 query；F05 下边恰在 64nm，只有边界接触，实际 MN0 应计 4 而 source CDL 仍为 5。这是证明计算来自几何的既有见证。
- W011 补齐“沟道对应哪个器件、实际有多少有效 FIN”的有限能力。完整 D/G/S/B 网络匹配、body、model/VT 与其它规则尚无本轮完整证明；不能把 5/7 相等写成完整 extraction equality 或 M1 完成。

### 行为要求

1. **同源纯组合。** 支持实际 W005 direct 及 W006 readback 经 W008/W009/W010 的组合；在同一捕获运行或认证 W007 结果。校验 geometry、semantic/query、physical/derived/drawn/formats 及所有实际消费的 rules 的 payload、source role、单位和 refs，不接受跨输入/跨 run 拼装。整个组件禁读盘/repository、禁调用 EDA、禁加载 spec/oracle/expected；domain/纯算法的自洽与 normalization 的捕获认证各守边界。保留 source、target、完整差异、原 query/body、W010 图/audits 和 unsealed attempt。
2. **channel 定位和覆盖分开。** 按实际 derived registry、exact 单位、quality/trim/tolerance 求 seed 与 channel 的精确交集，保留 seed/xref/query key、原 POLY/active/channel 来源和覆盖。正面积交集提供候选，不能凭名称、Y 坐标、最近中心或排序挑一个。完整关联须检查全部 source devices 与 recognized channels 的 one-to-one 关系，缺失、多解、冲突、需要 reduction 的情况定位说明，不静默丢弃多余 channel/seed。相同身份的多份证据保留各自来源，不能把它们误算成多 finger。

   方案须明确唯一定位关联与完整区域 annotation 的不同：部分覆盖不能冒记 full coverage 或完整区域身份；现行 owner 并未规定所有定位 seed 都必须覆盖整个 channel，不能新设一个隐含的全覆盖输入门槛。保持 exact 交集/coverage 和候选/关联的证明边界；无法从既定合同证明的关联给出明确不足/歧义结果。W011 不交付通用 annotation state 或 component net labels。
3. **从几何独立计量。** 对每个真实 channel 逐一判断 FIN：正面积 crossing 才可能计数；完整 x 覆盖及完整 active y 包含按精确集合/有理值比较，等号允许；仅边/角接触和范围外 FIN 不计，partial crossing 定位 unsupported。按 channel 的 X/Y 两维归属，允许同一长 FIN 在不同 channel 各自产生 crossing；不按全局 FIN 数、query bbox 高度、面积除法、CDL NFIN 或固定 5/7 反填结果。不改变 raw FIN，不在 DeviceIR 储存长期 fin-track 真相副本。

   原 FIN records/重数及几何重复关系必须保留。现行 `distinct qualified FIN rectangles` 尚无已验收的重复/重叠 FIN 计数见证；执行方案先查明独立物理 FIN 的依据，不默默按 record 双计数或按 bbox 去重。不能唯一解释的变体不得声称有效计数，按现有“无法证明落在 profile 子集则 typed-unsupported”保留证据并定位；如需新增物理解释，带具体反例交 PM，不用自造测试冻结新答案。
4. **参数核对与 intent 分开。** 报告每 channel 的实际 count、channel x 长度、逐个 crossing 的实际 FIN 宽度及 exact 来源；与 source/current CDL 的对应 canonical axes 做明确有限比较，保留实测值、声明值、全部可判差异。正常得到 5/7、L=4nm、W=2nm；上述变体得到实际 4 对声明 5 的差异。允许成功计量同时携带 mismatch，或返回保留已算事实的定位错误，接口在方案中明确；绝不能写成一致。NF/M=1 的准入沿用 W007/profile，不声称从几何独立测出 multiplicity。target 仅是独立 intent，修改 target 不改变 source 几何结果，也不能以 target 尚未达到为 source 提取错误。
5. **局部拓扑只引用，不改写。** 关联的 G/S/D region/node/component refs 须回到同一 W009/W010 的实际对象，有序 S/D 沿用既有解释；两 channel 可引用同一 G node。不得按 DeviceId/net 名造边、跨 channel union S/D、合并两 body 域或消除 W010 enclosure violation。没有完整 net overlay/body 时不宣称 D/G/S/B net 匹配、TOY_N/P/VT 的独立几何验证、全部 T03/T08、LVS、no_change 或 production assurance。T02 的全 FIN width/pitch/phase 规则义务保留，计数通过不替代它。
6. **公开结果可重建且诚实。** 使用 closed/versioned、递归不可变的 DTO 和 canonical wire/digest；refs 绑定捕获、scope、单位、profile、channel/FIN/seed 和实际已消费 owner。公开 constructor/decode 验证完整关联、crossings、计数、来源与差异，拒绝漏项、额外项、伪造计量/一致、跨源引用、可变 alias 或丢失已有违规。重复重建稳定；record 重排可改变来源 refs，不改变同几何/证据关系的计算语义。预期输入/能力问题定位并保留 completed；意外异常、中断保持原对象及已有 cause/context/suppression，包括嵌套 W010→W009→W008→W007 解码及处理预期错误后再次构造结果的路径。
7. **工程与资源。** 遵守 Python 3.10+、strict typing、模块 owner 和具名依赖守卫；不得引入 legacy 或 tests/support runtime 依赖。最终版本运行原 1465 项及新增必要回归、双解释器完整矩阵、typing、新包构建和双干净安装源码外 direct/readback smoke。记录完整源码/测试/配置身份及原命令输出，review 后若变化只按影响重核。有限输入上的耗时、wire 大小/保留链和资源限制据实际数据披露；考虑已有重复捕获认证成本，不把样本运行值当最大输入/生产性能保证，不为本任务顺手重构上游 wire 合同。

### 验收

| 项 | 输入/条件 → 预期 | 正确性依据与验证 |
| --- | --- | --- |
| A1 同源组合 | 实际 direct、W006 caller-read readback → 同源 W007/W010 组合，无 IO/发布，输入及 attempt 不变；异源或篡改 owner 拒绝 | 实际捕获与来源错配负例；禁止用手造 DTO 替代两条主路径 |
| A2 正常完整结果 | 两 channel 唯一关联 MN0/MP0；完整 crossing 集合为 5/7，L/W 有限核对一致；同一 G、四个有序 S/D 回链准确，18 FIN 全保留 | 独立手工几何/identity/集合表与 oracle 对照，验证整个集合，不只断言计数 |
| A3 几何边界 | 完整/partial/零面积、等号、同 Y 不同 X、同 FIN 跨两个 channel、大整数与精确有理 seed、重排/重复/重叠 | 独立精确算术见证；partial 不取整，无法解释的重复不冒报计数 |
| A4 定位边界 | seed 缺失/多解/冲突、一个 POLY 多 channel、同身份多个 seed、partial coverage、未消费 net seed | 精确 trim 及 coverage；区别定位事实与全区 annotation，所有 source/channel 均核对，无名称或序号 fallback |
| A5 source 比较 | 现有 extraction_mismatch 得到 4 对 5；另覆盖 L/W 不符及多个可判差异；target-only NFIN/其它 delta 不改变 source 计量 | 使用原失败 overlay/独立临时变体，不改固定 fixture/答案；全部 typed differences 与实测值可定位 |
| A6 公开合同 | constructor/codec/digest 完整重建，错 ref/漏 crossing/假一致/重复 alias 拒绝；正常及错误链的意外异常原样传播 | 本次新边界与实际嵌套链的定向注入，含预期问题后二次认证异常及一次集合快照 |
| A7 scope | 本地图和 T05 违规保留、body 隔离；未知/矛盾已消费 operator 拒绝；未消费声明保留 | 正常/via_enclosure 组合及异策略负例；不误升 model/VT/net/body/规则/运行 assurance |
| A8 工程交付 | 最终源身份绑定双完整回归、typing、包/双安装及新独立 review；必须修正项 0 | 命令、环境、源清单/快照、包与实际安装来源、输出和限制均可跨 session 访问 |

新输入格式、图/报告或 fixture 使用预期待决：无。以上只是现行 synthetic profile 的内部派生草稿；生产单 cell 缺 body/tap/rail 的 [U06](../roadmap.md#production-body-evidence) 保留，不把 toy body_context 必填推广为生产要求。

## 方案与决定（执行准备，PM 接收）

执行细化已记录于[方案](W011/plan.md)，未参与设计的 reviewer 完成[独立方案 review](W011/plan-review.md)，必须修正项 0；方案/报告提交 `1b3c409`。方案明确唯一定位与 exact coverage 分离、逐 channel/FIN 几何资格、重复/重叠 FIN 独立性不明则保留诊断、source 比较与 target intent 分离，以及完整公开重建。旧 stored fin-track/query-count 逻辑调查后不迁用。具体未决重复 FIN 扩展样本随方案交 PM，不改已验收 fixture/答案。

## 执行结果（执行）

### E1 恢复与实施准备（2026-11-09，执行）

`/root` 从 `/workspace/Layauto` 干净的 `work@61775e8fde6e9ea247ec08a32067c44c3be48ff8` 恢复；实核远端 main 同 SHA，W011 准备 head 为 `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`，已 fetch 并切回原 W011 分支。读根/协作/环境/current-work、W011 引用的架构/owner/fixture及 W007–W010 合同；无局部 AGENTS。提交身份沿用项目 noreply。

先完成独立方案 review，再按分离 worktree 实施 core 与测试，由本执行者集成 normalization/codec。双解释器基线与工程环境由独立执行辅助保存命令/输出；最终 A1–A8、测试/包及独立代码 review 结论在完成后追加。本记录不代写 PM 阶段、验收或集成事实。

### E2 实现、代码复核与最终验证（2026-11-09，执行）

产品修正提交为 `8917d38d916c914bfa785cb116982f3f299b38de`；最终被测源码、测试和配置冻结于 `e89bdaa6a091f56cfaf7862dced7232d34e22514`。新增 140 项回归，总计 1605 项，原 1465 项 ID 全部保留。262 文件的[清单](W011/verification/source-manifest.json)与[完整快照](W011/verification/source-snapshot.tar.gz)逐项一致，所有工程命令结束后再次核对；后续交付提交只补充执行、review 和证据文档，不把文档提交冒记为另一份直接跑过的源码。

最终 Python 3.10.22 / 3.12.14 全量分别为 **1605 passed / 12905.97s**、**1605 passed / 7310.82s**，命令均 exit 0；3.10 命令总耗时含 2603.347s 的 W011 互斥锁等待。双 strict mypy 均成功检查 54 个源文件，双工程及安装环境 pip check 通过。新 wheel/sdist 构建成功，分别从 sdist 建立 clean 3.10、从 wheel 建立 clean 3.12；100 个实际安装运行时文件与冻结源一致，源码目录外 `-I -B` 完整组合 smoke 分别以 620.633s、450.631s 通过。命令、UTC、环境、包身份、原输出及索引见[最终工程回执](W011/verification/receipt.json)。

两条实际捕获路径均由 exact geometry 得到 MN0=5、MP0=7，完整 crossing、来源、局部拓扑、T05/body scope 及 unsealed attempt 保留。原 extraction_mismatch 实算 MN0=4，对 source CDL 5 保留一项差异；target-only 变化不改变 source 计量。closed/immutable DTO、完整公开重建、全部可判差异与嵌套异常链由最终双完整矩阵覆盖。实现及 A1–A8 对应证据见[执行记录](W011/execution.md)。

三个独立进程的完整 Result 资源样本均完成，见[资源回执](W011/resources/receipt.json)。readback wire 为 136,461,405 bytes，整进程峰值 RSS 为 7,322,828 KiB；双矩阵/安装的 10s 观察另见[归档](W011/preflight/final-attempt02/)，其中最高采样 RSS 为 9,257,804 KiB。这些是 16 GiB cgroup、4 CPU quota 下的有限 synthetic 实测；constructor 认证包含在 build/decode 中，未单独计时，RSS 不是 W011 增量内存，也不构成最大输入或生产性能保证。

首轮冻结 `02725e2e90be6b3145be915be699aa64ce998ed7` 的 Python 3.10 完整结果是 **2 failed / 1603 passed**，旧 3.12 仅启动 collect 后中断、full 未运行；[原输出](W011/verification-attempt-01/pytest-310.stdout.txt)、[结束事实](W011/verification-attempt-01/attempt-closure.json)及[索引](W011/verification-attempt-01/evidence-manifest.json)完整保留。两项测试准备/入口边界错误已最小修正并在最终双完整矩阵通过，runtime/schema/fixture 未因它们改变。原 CR-01–CR-06、HG-01 及各阶段残留/修正复核保留在[独立代码 review](W011/code-review.md)及其附件，最终结论由 reviewer 自行记录。

重复/重叠 FIN 的独立物理解释、身份定位不足时仍可保留的 channel 几何计量等具体样本已交 PM，未修改 fixture/答案冻结新语义。交付范围仍为原 W011 分支；使用既有 noreply 身份提交推送后核对远端完整 SHA，以 Git 与交接回复记录最终交付身份。本节不更改 PM 阶段或验收，不合 main、不改 current-work、不删除分支或启动下一任务。

## Review 结论（reviewer）

2026-11-09，未参与调查、设计或实现的 `/root/plan_review` 完成[独立方案 review](W011/plan-review.md)，**必须修正项 0，方案可进入实现**。受审方案 SHA-256 为 `24a4d3b4c1f95851f35f77a0e6744af3c6618590741976882e7e2010ae38e94e`；PR-N01/02 为不完整计量摘要和完整结果资源测量的非阻塞核验提示，原文保留于报告。

方案阶段原记录（历史范围）：代码 review 尚待实现及工程证据完成后独立执行；本方案结论不替代代码 review、A1–A8 实测、PM 验收或用户另行要求的专门合并前 review。[交接要求 review](W011/handoff-review.md)仍保留其原准备范围。

2026-11-09，未承担设计、实现或正式测试编写的 `/root/code_review` 及独立几何/边界专项完成[代码与最终工程 review](W011/code-review.md)。最终被审源码、测试和配置为 `e89bdaa6a091f56cfaf7862dced7232d34e22514`，100 个 runtime 文件与产品修正 `8917d38d916c914bfa785cb116982f3f299b38de` 相同；262 文件 live/快照、双 1605 全量及原 1465 IDs、双 strict 54 files、新 wheel/sdist、双干净安装源码外完整组合 smoke、三项完整 Result 资源和实际门控证据均独立核实。[只读审计结果](W011/review/final-a8-audit.stdout.json)记录工程索引 SHA-256 `91fc8869f2b1cb3f15d76334f9577f6902f14c6b90e900a1b25f735311c4f077` 与资源索引 `2bdf899cf8d52e61aca4941b5f240a76379149f2837f7ea9ba56e27f5a6c6459`，原 CR-01–CR-06、HG-01、修后残留及失败/补修历史全部保留。

**独立 review 剩余必须修正项 0，A1–A8 对应代码和工程证据可交 PM 复核。** 此结论不代替 PM 验收或最终 Git 交接；执行者仍按原 W011 分支提交推送并核远端完整 SHA。资源数据仅为记录环境中的有限 synthetic 样本，constructor 包含于 build/decode、RSS 非增量内存；完整 net/body/模型、全部规则/工艺坐标、发布/no_change/Stage6 和 U06 继续后置。

## PM 验收与交接（PM）

2026-11-09：W010 已验收集成，本轮只准备 W011。接收未参与调查/起草的 reviewer `/root/w011_handoff_review` 及只读上游专项的[派发要求独立复核](W011/handoff-review.md)，必须修正项 0。受审准备稿 SHA-256 `faf0a6a31d1d4acb0772ad0d328a6726e050fdb58c737c6c34c76daa8d6be3dc`；本次仅追加阶段与 PM 接收记录，未改行为要求/A1–A8。partial seed 和重复/重叠 FIN 的具体输入→结果表属于执行方案及其独立 review 的必读落实提示，不是新的用户决策门。

**W011 可执行，交独立执行 session 先做方案 review 后实现。** 尚无 W011 产品实现、测试或验收结论；本轮只做文档链接、diff、范围与恢复身份检查，未运行产品测试/生成器。准备文档及review提交推送上述 W011 分支，完整发布 SHA 以 Git 与交接回复为准；main 保留已验收版本，未开启下一开发任务。

### 独立执行 session prompt

```text
按 Layauto 项目规范，以执行角色完成 W011“沟道身份匹配与 FIN 计数草稿”。
从 codex/w011-channel-identity-fin-count 的 PM 准备提交恢复；起点 main 为 61775e8fde6e9ea247ec08a32067c44c3be48ff8。先核对远端完整 SHA、工作区和适用 AGENTS；读协作/环境规则、current-work、W011 及引用的架构、实际 owner/fixture 和 W007–W010 合同。
先细化方案并由未承担设计者独立 review，再实现 A1–A8。把同一捕获的 W007 identity/seeds 与 W009 channel、W010 局部图组合；query 只提供身份和定位证据，FIN 资格/数量必须从真实 exact geometry 计算。正常 MN0=5、MP0=7；extraction_mismatch 必须实际算得 4 对 source CDL 5。source 比较与 target intent 分开，seed 定位与覆盖分开；重复/重叠 FIN 无依据时不默计。按任务要求保留局部拓扑、原 T05 事实、body scope、来源和全部差异。
完成 closed/immutable DTO、完整公开重建及嵌套异常链验证，原 1465 项及新增回归、双解释器全量、strict typing、构建与双干净安装源码外组合 smoke；保存最终身份、命令、环境、输出与资源限制。独立代码 review 后修正复核全部必须项，保留原 findings。
提交推送原 W011 分支，使用项目既有 noreply 身份，核对远端完整 SHA，交回 PM。不自行验收、合 main、改 current-work、删分支或启动下一任务。完整 net/body/模型匹配、T02/全部规则、工艺坐标、发布/no_change/Stage6 及 U06 仍按任务边界后置；新增关键解释带具体样本交 PM，不改 fixture/答案冻结新语义。
```
