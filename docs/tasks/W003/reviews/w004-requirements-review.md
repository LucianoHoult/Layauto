# W004 对原规划及人工意见的独立要求复核

Reviewer：本轮独立 reviewer `/root`；2026-11-02。未参与 W004 实现。本轮只写本报告和 W004 reviewer 追加记录，不代作 PM 验收，不改变既有决定。

**结论：原 W003 文件边界、独立答案、22 个反例目的及有效人工修改要求总体保留；发现 1 项必须修正的 P2 局部 helper 精度问题（REQ-01）。** body rail 匹配将精确有理数向下取整，能把不相等的 raw annotation 当作本地 rail。正常交付坐标及原 29 个见证的答案没有因此被推翻。其余未发现实质遗漏或无依据后置；现有“已验收/0 findings”未作为本次结论依据。

## 1. 版本、方法与实际范围

| 身份 | 本次核对事实 |
| --- | --- |
| 初始 checkout | `/workspace/Layauto`，分支 `work`，HEAD `da55ca656e5e38caba1e7f47483137c68c044907`；staged/unstaged/untracked 均为空，三个指定提交最初不可用。该 checkout 未改动 |
| 独立副本 | `/workspace/work/layauto-w004-review`；本地独立 clone 后仅获取目标远端分支，checkout `codex/w004-task-convergence`；起始工作区干净 |
| 被审交接版本 | `c46952a9085aecf3aa17f60346b61bc2870d2614`，取得时远端 `origin/codex/w004-task-convergence` 同 SHA |
| 实物 / 准备基线 | `633e3feef8062565019838f2d270e89b7f81c4ed` / `9f6735dcede8e8b2135f89ff10f079a752ed758b`，均实际取得；提交链为 `9f6735d → 633e3fe → c46952a` |
| diff 范围 | 检查 `9f6735d → 633e3fe` 的实际修改及最终文件。`633e3fe → c46952a` 仅改 8 个文档/接收记录路径，fixture、support、合同、examples、图及既有独立 review 未变 |
| 环境 / 写入 | Python 3.12.14，标准库定向检查；body 冲突探针调用被审局部 helper。未安装依赖。仓库仅新增本报告、追加 W004 reviewer 段；未提交、推送、合并、删分支或启动 W005 |

先读 AGENTS、README、协作规则，再从 [W003 原规划](../../W003-m1-fixture-contracts.md)文件范围/验收表与 [manual 原文](../manual-verification.md)提取要求。按职责并行只读核对原规划、body/tech、raw/反例、共享记录/报告；最后统一裁定和写入。MR-076/078 只作导航，关键判断回查 MR-002/004/019–023/030/033–040/046/051–052/058–076 原文。随后对照 W004、contracts、revision-evidence、全部 8 份已有 review、实际 fixture/support/图/报告。W005 仅用于核对后续归属，未执行其任务。

架构原文核对范围为 [architecture](../../../architecture.md) §1.4、§2.2–2.3/2.7、§3.1–3.6、§4.8、§5 的事实/annotation 边界、§7.1/8.1、§10.2–10.6、§11 的 importer/中立记录及依赖边界、§12.1–12.8；特别区分 raw 获取、解析、Stage 2 几何/语义关联和 Stage 6 输出验证。没有把产品架构的全部未来实现自动加入本轮样本交付。

### 采用既有证据的身份与边界

对 [已发布交付包](../delivery/w004-20261031/W004-delivery.tar.gz) 做选择性身份核对，未重跑全包验收：

- 实际 tar SHA-256 为 `3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39`。
- 包内 `review-input-r3/SHA256SUMS.json` 共 145 项，SHA-256 为 `9136e0509ab50e03ea260eb0d1ecaedfb4aa6a58cda17a5cc926d715de0fbd76`。当前仅 current-work、W004、W003 任务、manual、W003 README 五个文档与其不同，分别属于后续交接/接收/导航；选取的 fixture、helper、examples、图、contracts、revision-evidence 共 131 项均保持相同 bytes。
- r2→r3 仅 W004、revision-evidence、w003_verify 三文件变化，raw/query helper/cache 未变。选取的独立几何脚本/结果、raw 脚本/结果及冲突结果共 8 个包内文件逐一匹配包内 manifest；审读其方法，确认几何/raw 正向核对不 import 生成器作为答案。
- 因此采用 [independent-r3](independent-r3.md) 中全部 29 个实际 overlay 的独立缺陷证明、精确 REAL8/完整 CDL/几何读回，以及再生成实物比较；采用 [owner-raw-r3](owner-raw-r3.md) 和 [raw-r2](raw-r2.md) 中已修复声明冲突的定向结果。它们是**既有证据**，不是本轮重新运行所有负例、生成器或工具。
- 旧 IR1–IR5 原文和修复经过仍保留；本轮 REQ-01 是另一个局部精度问题，不把旧 finding 改写为未修复，也不把旧最终结论当作全称证明。

## 2. 原要求 → 有效解释 → 实物 → 证据 → 结论

下表 `F/` 指 `tests/fixtures/w003_m1/`，`H/` 指 `tests/support/`，`D/` 指 `docs/tasks/W003/`。行号均基于上述被审提交，MR 原文是要求来源，不用汇总表替代。

| 原要求出处 | 当前有效解释 | 实物位置 | 核对证据 | 结论 |
| --- | --- | --- | --- | --- |
| W003:30、76–80；MR-025/027/028 | source/target 完整语义、flat 矩形子集、精确单位；未支持结构不能忽略 | F/source.gds、source.cdl、target.cdl；tech/formats.json；D/contracts.md:9–10 | 本轮直接解码 GDS 并比较基线；仅移除已批准 LB/CUTB/TN/TP，余 40 图形层/坐标不变；source/expected 40 图形相等。完整 CDL 采用同身份 r3 独立证据 | 已落实 |
| MR-002.1（manual:273）；架构 §2.2/12.5 | 1nm 有 versioned toy 来源；raw REAL8/nominal/canonical/制造格/索引格分开，不能 GCD 推单位 | F/sources.json 的 unit_chain；tech/formats.json；expected/unit-provenance.json；H/w003_verify.py:35–70 | 单位原 bytes 与准备基线一致；r3 独立 Fraction/half-ULP 和声明冲突证据适用；C01/C19/C20 保留。共享 unit encoder 的范围公开 | 已落实；未宣称独立单位 writer 或生产精度 |
| MR-002.2/003、MR-023 | 实际尺寸、精确 profile 值、DRC 下限各归其源；无来源的 gate spacing 不编造 | F/sources.json dimensions/key_derived_values/rule_sources；tech/physical.json、rules.json；independent-design-answer.json | 40 本地+6 外部尺寸与实物对账；FIN 2/10/24、gap 8、gate L=4 和无独立 spacing/min-width 的限制明确；T03/T05/T07 正负例仍在 | 来源/适用表已落实；不声称逐个尺寸负路径全覆盖，见 §4 |
| MR-004:313–316、MR-023/039；架构 §4.8/12 | 分类是唯一真实输入，不是另一份阅读副本；所有旧字段及依赖同步 | F/tech.json 的六 owners、tech/{drawn,derived,physical,formats,coordinate,rules}.json；sources.json owner_consumers；H/w004_support.py、w003_verify.py、w004_query.py | 旧 tech 字段归属逐项可追；FIN 值集中在 physical，单位在 formats，annotation tolerance 在 derived；入口实际读取/固定合同一致性校验。既有 9 类冲突及 r3 剩余单位探针均拒绝 | 已落实；MR-040 后置未取消此义务 |
| MR-005–012/015–019/024–025；W003:36 | 完整 FIN 背景、5/7、D/G/S/B、mandatory 规则和非连接关系不能因 no_change 省略 | F/spec.json、oracle.json、expected/layout.json、independent-design-answer.json；D/fixture-layout.png | 18 FIN 保留；40 drawn/14有效导体/8本地边/6本地分量；独立几何与图一致。旧本地 body 边由后续 MR-046/D1 替代，不机械保留旧数量 | 已落实 |
| MR-046；W004 PM1 D1=A（W004:303）；架构 §3.6 | 本地 flat cell 无 tap 可有效；外部只读、绑定实际输入、独立 scope；按精确几何再关联 rail | F/body/context.json、tech/physical.json:72–109、oracle 两域答案；H/w004_body.py | 正常外部 6 形状不进 GDS；body 接续90/100nm、rail10/10nm、tap包围8/2nm可独立复算；C22+7 body 实际 overlay 逐个先过 binding 再命中目标 | 样本/两域答案落实；**helper 精确 rail 匹配有 REQ-01 缺口** |
| MR-019/020:690–692；MR-051 经052收窄 | CUT/孤岛迁专例须保留分片、同标签不并、同格不连、2nm间距及披露；不要求专例另造完整产品链 | F/special/cut_islands/{spec,oracle,source.gds}；H/w003_verify.py:311–319；D/图及报告 | 本轮独立 GDS/整数差集：4图形，LB剩余面积72nm²，3分量0边，三对距²=4/4900/6561；两片同32×16桶仍不连通；R08/R09和A_REMOTE保留 | 原测试目的已落实 |
| MR-021/022 | MARK 保留、无注释、非导体，不凭标签补事实 | F/spec/oracle/expected；D/图、报告 | 主例仍有 MARK，报告明确 unannotated/nonconducting；未混入 connector/导体集合 | 已落实 |
| W003:31；MR-029/030.1 后被034替代 | 一套选定 Calibre-like raw；四 capability 不等于四文件；旧 W003_QUERY 撤下 active 路径 | F/query/{dialect,requests,header}.json、raw/；H/w004_query.py；F/README:95–122 | 9raw→2/4/2/8 records；legacy 六来源指纹/合成身份保留；active helper/query 无旧 toy 方言；不虚构真实 capture | 已落实；真实方言验证仍未完成 |
| MR-030.2:977–1007、MR-031–034 | normalized 自身可读、具名坐标/对象；保留 full vertices、exact、quality、原文回链与独立期望 | F/query/normalized 四文件；requests/dialect；H/w004_query.py | 本轮标准库独立核对10 polygon、146字段、558处实际位置/lexeme/hash；nXref+NET NAMES join为1/n_a/A、2/n_y/Y、3/n_lo/VSS、4/n_hi/VDD；原语义/几何除批准迁移外不变 | 已落实；具名字段分组方式未被冻结；consumer 截断另见 REQ-01 |
| MR-035–038；W003 header/closure | source/top/netlist/deck/map/runset/include/preprocess/options/raw/版本同源；无缓存仍可解析，错误缓存不得覆盖后通过 | F/query/header.json 的17 leaves/9raw；F/site_config.yaml；H/w004_support.py；C06/C07/C21 | 本轮实际绑定/定位核对；C21只把A改Y，其余cache与正常相同，raw/provenance仍有效，故不是意外hash错误；新增body/六owner纳入闭包 | 已落实 |
| W003:32；MR-039/041/058–064 | site只选择输入；三核心输出required、不可表示/溢出拒绝；mandatory不能被policy关闭；四维检查分开 | F/site/export_policy/validation_policy/limitations；D/contracts.md:15、34–45；C19/C20 | 三artifact实际size/hash；11唯一check ID，5 deferred；正常requires_review，required fail/error reject；重复outputs一致性有冲突证据 | 已落实；输出/发布实现属后续 |
| W003:33；MR-026/036/038/072–074 | 中立版本记录、producer/consumer、typed IDs/refs、exact编码及非法组合；不能用样张预制state | D/contracts.md:20–46、examples/schema.json/records.json；F/expected/layout.json | 本轮20正常记录、136 typed refs、133文件hash/JSON pointer可解析；样张example_only，layout明确非完整runtime snapshot | 样张合同已落实；DTO/codec/冻结/CAS实现后续 |
| W003 E4/R1 F1（任务:159、183） | pre-context descriptor覆盖operation/run/head/lineage/key和全部实际选择/bytes，无未建立context | D/examples/records.json:452–634；H/w003_record_examples.py:114–124、405–438 | 本轮重算27路径摘要、5selector与27份内存bytes改变均敏感；实际落盘变更/拒绝旧摘要采用已核身份的原专项证据 | F1保留；未把内存probe称为产品持久化 |
| W003 E4/R1 F2（任务:160、184）；MR-034 §6/073/075 | 真坏raw→对应header→独立fixture-read ToolRun→Parse→StageFailure/localized→failure RunRecord | D/examples/failures.json:6–170；F/failures/missing_terminator/ | 本轮实际坏DEVICE INFO恰缺END OF RESPONSE；逐bytes/hash与全部链引用一致；无正常raw冒充坏输入 | F2保留；产品失败管线未运行 |
| W003:34；MR-058–070/074–075；架构 §10.2/10.6 | 正常 GDS/CDL/JSON、manifest/validation/reporting/terminal 与人机报告都有最小样张；bytes与语义分开 | F/expected/*；D/examples/{records,report.expected}.json、report.expected.md | 三核心实物存在且hash正确；机器保留无delta/candidate、whole-cell constraint、五类0变化、derived refresh；人读保留新数量、scope、检查及限制并指向机器报告 | 已落实；人读精简未形成已证实的合同遗漏 |
| W003:35；MR-075/076 | 8类失败的阶段/产物/冻结例外与terminal事实各自成立 | D/examples/failures.json、contracts.md:48–64 | 本轮核对pre_context、sealed_no_publication、freeze、export、check fail/error、report、terminal storage；无ECO/禁止产物、freeze无RunRecord、terminal失败不造发布指针均保留 | 已落实；是未来断言而非产品运行结果 |
| W003:36/77/79；MR-004/034/070 | oracle须有独立依据，不能输入/答案一起改错自洽；重复生成独立于正确性 | F/independent-design-answer.json、spec/oracle/sources；D/既有独立脚本/结果 | 本轮与9f坐标/语义对账、实际stream和专例整数复算、独立raw检查；既有r3从stream/CDL及整数/Fraction推导。设计答案旧full-cell专例建议由README明确标历史方案 | 未发现正常输入与答案共同改错；限制公开 |
| W003范围/非目标、MR-055/065；架构 §11.14/12.8 | synthetic、按描述重建、tool-captured、真实运行分开；无legacy runtime依赖 | F/limitations.json、query/dialect.json；D/contracts/handoff/revision-evidence；H/w003_*及w004_* | 实际diff未实现产品；工具null/not_run/deferred、production_matched_body_evidence=false一致；legacy仅格式来源，不import其runtime | 已落实；真实G1–G5门未豁免 |

### 原22个目的及新增7个body见证

本轮逐项比较 `9f6735d:failures/cases.json` 与最终清单：原22例的 id、expected_issue、phase、future_runtime_assertions、executed_as_product_run 全部保留；新清单加 original_id。P/S/E分别为pre_context/sealed_no_publication/export的**未来产品预期**；全部保留reject、0 ECO、无正常manifest的断言。

| 原ID | 当前实际见证 / 原目的 | 阶段 |
| --- | --- | --- |
| C01 | source unit=2nm vs selected1nm，依赖重绑 | P |
| C02 | DEVICE INFO缺END OF RESPONSE，删除对应缓存；未给xref捏造结束符 | P |
| C03 | NET NAMES声明5、实际4，删除受影响缓存 | P |
| C04 | polygon结构p→q，拒绝未知几何token | P |
| C05 | geometry precision20000→0，拒绝无效单位绑定 | P |
| C06 | nXref bytes漂移，故意不重绑raw hash | P |
| C07 | header source top错绑 | P |
| C08 | Q17/Q93均映射MN0，多对一不支持 | P |
| C09 | NF=2，多指不支持 | P |
| C10 | Q18→MN0第三映射，需device reduction | P |
| C11 | NFIN={2+3}，表达式不支持 | P |
| C12 | INCLUDE，依赖directive不支持 | P |
| C13 | target L=4n→5n，FIN仍5/7也不是no_change | S |
| C14 | MY x左边80→79，M1间距5→4，计数不变 | S |
| C15 | VN移出LN enclosure | S |
| C16 | ON上边70→64，物理N4 vs CDL5 | S |
| C17 | 添加TEXT，不得丢弃 | P |
| C18 | 非矩形，不得bbox替代 | P |
| C19 | output DBU=2nm，奇数坐标不可表示 | E |
| C20 | output tick=1/10⁹nm，超32-bit范围 | E |
| C21 | 正确raw/provenance下cache A→Y内容漂移 | P |
| C22 | 从分类physical owner删除body_context/2；缺必需支持目的不变，无本地BTAP本身不是错误 | P |

新增 missing_body_context、body_wrong_binding 为P；body_wrong_type、body_disconnected、body_ambiguous、body_enclosure、body_wrong_rail 为S。本轮真实复制底座并应用C22及这7例的replacement/remove，外层hash均正确、逐个命中指定原因；错rail例只改目标rail声明，未夹带旧异型body重叠。raw专项另真实应用C02–05/C21。其余几何overlay完整执行采用既有r3证据，未声称本轮重跑全部29例。

### 后置和后续归属

| 原要求与先后关系 | 当前有效边界 / 归属 | 结论 |
| --- | --- | --- |
| MR-040候选 → W004 PM1 D2明确后置 | 配置机制精简在改变入口/优先级前另作方案；本轮仍分类、唯一owner实际消费及重复outputs冲突检查 | 明确后置，有依据；未将MR-004推迟 |
| MR-074-Q1 → W004 PM1 D3 | 本地GDS/CDL/JSON语义读回、production downstream open/syntax、Virtuoso/SKILL dry-run、旧virtuoso_readback分别保留；旧scope在真实工具集成前明确 | 身份/表格同步已落实；旧生产scope明确后置，非删除或改名豁免 |
| MR-051 → MR-052收窄 → MR-054/056 | 本轮只澄清32×16人为专例和coordinate/component引用；F/tech/coordinate.json及layout声明example_only/非完整runtime | 样张已落实；完整Stage2坐标/occupancy/CSP/DTO/codec/CAS属后续，不能恢复旧扩大要求 |
| MR-033-Q1/038-Q1及MR-039确认原则 | 所选raw/schema规则的通用接受/拒绝、safe-load测量边界、第二合法输入在W005输入条款1/4/5及A2–A5 | 后续产品开发有依据；固定helper不是通用loader，但已有精确消费不得静默取整（REQ-01） |
| W003/W002完整闭环义务 → W005组件拆分 | W005 §“PM已确定的任务拆分”保留pipeline/pre-context F1/F2审计、Stage2状态/body/mandatory/CAS、Stage6导出/报告/terminal三组接收方 | 后续开发，未称W005读取成功等于M1完成 |
| MR-013候选、MR-014局部颜色说明；MR-026候选 | 未批准新增M1-cut/color全套样本、预检/诊断透传产品方案 | 非本轮必须项，不制造缺陷或审批门 |
| 原A/B“未整组确认” → MR-078/P10后续决定 | 保留历史用户答复身份，不重写为逐项亲自确认；当前不重建审批前置 | 历史记录不阻塞本轮review；本报告不再次征求D1等已定决定 |

## 3. Finding

### REQ-01 · P2 · 必须修正：body rail 匹配把精确有理数截为整数

**原要求。** MR-002.1要求精确单位/坐标不被取整改写；MR-030.2（manual:1003–1004）明确“其它输入须按单位合同选exact rational/decimal等表示……不能……取整”；MR-034 §2要求精确换算而不移动几何。W004 PM1 D1明确几何关系不成立不能通过。当前自身合同 `tech/physical.json:77、87、109` 要求精确body/rail对象及先几何后语义关联，derived的toy_m1匹配容差为0。

**实际位置。** [H/w004_body.py](../../../../tests/support/w004_body.py):42–44 的 `val()` 对normalized `bbox_nm`逐坐标执行 `numerator // denominator`，随后以该整数bbox匹配本地rail。`w003_verify.py:258–274` 的 `witness()` 直接调用此helper，未先执行正常整包验证所用的 `raw_answers()` 整数性检查。

**问题证据。** 在独立副本保持GDS、CDL、body context及tech不变，仅将 `query/raw/net_shapes_n_lo.txt` 的VSS rail两个右侧顶点x从900改901。按原方言 `(y,x)/20000 µm`，raw精确bbox从 `[0,48,45,58]` 变为 `[0,48,901/20,58]` nm，即右边45.05nm。同步重绑实际header/hash，并从该raw重建对应normalized；外层bindings检查通过。原方言允许整数raw刻度，未要求刻度是20的倍数；这个矩形能精确解析，却已不等于实际本地MN的 `[0,48,45,58]`。

本轮实际调用 `check_body()`，仍返回MN0→VSS、MP0→VDD两条正常关联；原因是 `901 // 20 == 45`。该结果由helper主动改了比较值，不能算“actual raw annotation on that local exact rail”已经成立。若此局部helper只接受整数nm，也应显式拒绝非整数，而不是截断后接受；修正不要求扩大支持子集。

**影响与限定。** 这是本轮新增body验证辅助对既有精确关联合同的落实缺口，可掩盖小于1nm的raw/GDS rail不一致。它影响该helper及依赖它的负例验证可信度，不能用“产品实现后续”免除。另一方面，正常fixture及原29见证使用整数nm，独立坐标/答案核对成立；正常整包 `verify()` 会先经 `raw_answers()`，该前置实际拒绝本探针。因此不声称本次原包错误通过整包验证、不推翻正常body答案。当前环境无KLayout；完整 `witness()` 未执行，只核对其源码调用次序，不把推断写成实测 `no_defect`。

**建议修复范围。** 仅在 `w004_body.py` 用Fraction精确比较，或在整数子集边界显式验证分母整除再比较；保留上述一个重绑raw的定向拒绝见证。复核正常两关联、C22/7body见证及这一个精度探针即可；无需重写fixture坐标、架构、D1、tech模型或实现完整Stage2。修复者更新受影响证据后交独立定向复核，本review不代修。

## 4. 疑点裁定、证据不足与可选改进

- **关键层规则负见证。** MR-002.2的来源/规则/适用表及既有T03计数、T05包围、T07间距反例均在。原文允许未有来源的gate spacing保留缺项，也没有冻结“每个T02维度各新增一个负例”的数量要求。本轮未发现专门的FIN width/pitch或gate L几何负路径证据，故不声称这些负路径已逐项运行；不能仅据此新增逐维度测试验收门。它不是另一个必须修正项，也不把它伪装为W005已接收的几何任务。
- **人读报告缩短。** 原人读说明的一些candidate/derived细节仍在配套机器报告和records，human保留关键no_change/数量/两域/required/deferred/requires_review及配套入口。W003要求最小样张，未冻结排版和重复字段；恢复数句解释可改善易读性，属于可选表达，不列finding。
- **独立性。** 整数/Fraction和独立reader是另外的核对路径；source/expected共享unit encoder的部分已披露，未将其说成完全独立writer。仅字节可再生不证明正确，已有包/审查状态也不证明本轮无缺口。
- **没有将缺产品能力列为缺陷。** 通用parser/loader、完整生命周期错误处理、真实工具和生产门未运行属于明确范围边界。除REQ-01外，未发现必须另补证才能判断本轮正常样本答案的实质缺口。

## 5. 本轮命令、结果及未验证范围

启动/版本命令在原checkout和独立副本分别执行，结果见§1：

```sh
git status --porcelain=v1
git branch --show-current
git rev-parse HEAD
git remote -v
git worktree list
git cat-file -t <三个完整SHA>
git fetch origin codex/w004-task-convergence
git diff --stat 9f6735d 633e3fe
git diff --name-only 633e3fe c46952a
```

| 本轮实际检查命令/方法 | 结果及界限 |
| --- | --- |
| `python -B -`：tarfile读取r3/r2清单，对实际文件逐SHA-256比较，并核对选取脚本/结果 | §1列出的145/131项身份及8个证据文件匹配；只做采用证据所需身份检查，未重跑8,988项验包/patch重建 |
| `python -B -`：`git show 9f6735d:<path>`，struct直接解码source/expected/special GDS、整数矩形相减/距² | 主例仅4个批准移除项，其余40不变；专例72nm²、3组件、距²与同桶结果见§2；无support import |
| `PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004-requirements-review/raw/check_targeted.py` | exit0；10polygon、146字段、558回链；C02–05/C21真实replacement/remove及F2同源通过；标准库独立实现，无support import |
| `python -B /workspace/work/w004-requirements-checks/records_check.py` | exit0；20正常、8失败、133文件refs、136 typed refs、3artifact、11check IDs、5deferred、8义务表一致；27路径＋5selector＋27内存bytes摘要敏感；F2及coordinate scope通过，无support import |
| `python -B /workspace/work/w004-requirements-review/body/probe.py /workspace/work/layauto-w004-review /workspace/work/w004-requirements-review/body/reproduced`；另实际copy/replacement/remove检查C22＋7body | 原8见证均在正确binding下命中目标；正常两链、40+6尺寸及专例答案成立。REQ-01的901/20变体被check_body误接受；从原文件AST原样提取的raw_answers前置拒绝同变体；重复复现需换不存在的输出目录 |
| `view_image` 实际查看 D/fixture-layout.png | 四域图明确本地无BTAP、18FIN/5/7、外部虚线边界、不导出、CUT3分量/2nm；图与当前scope同步 |

raw定向脚本SHA-256为 `7aab8d24b773107db765bf48b784a28fe44d31a05f7ae5648f39e17a486109a8`，结果为 `8a66927875a35f1fcb29ccfca750217aa572d8e1e5e77f449138c5d85f1c05c7`；records脚本为 `3406ef73d7f2a625137a1a2a2394fc4e733f5fa3b29516ae53b27e2729c822b6`，结果为 `78ccb702921585a27ab545c40ff5b04331bcdfe5f5969c88ce260f5b44df1cdd`；body精度复现脚本为 `796fe17090d1dc909cde01f282d9774dcf6ce4d6caca8029acfc73033b9695c0`，结果为 `0c9720a953c7cd57050676e32a1b8151e2b7c4be9f6fdf7e19378cdedd424729`。本轮脚本/输出另保存在本机审查包；云环境未能创建线程指定的下载目录，未声称已上传附件。REQ-01完整复现代码见附录，可在相同提交另行重建；关键输入、实际结果和影响均已写在本报告内，不以临时目录作为唯一依据。

未执行：全量生成/验包/无关pytest、完整witness（KLayout未安装）、产品parser/runtime/Stage1–6、publication/CAS/恢复、完整grid/CSP/DTO/codec、生产PDK/Calibre/LVS、downstream生产工具、Virtuoso/SKILL或旧readback、生产上传。既有工具读回/再生成和未在本轮重跑的overlay证据均按§1限定采用，未冒充本轮新运行。

## 6. 对 W005 的影响与交回

**无需改变 W005 的输入定义或既有正常验收答案。** 40本地图形、独立只读body context、九raw/四capability、六tech owner、原22＋7见证及独立答案保持。REQ-01应在辅助验证中修复并定向复核；W005及后续Stage2不得照搬这段整数截断逻辑。W005仍按既定边界读取精确值及绑定，外部物理关联/`body_complete`由后续Stage2承担，不把本次finding转成在reader实现完整body提取的新要求。

交回PM：1项P2必须修正，受影响范围仅上述body helper精度及定向证据；由后续执行修复后安排定向复核。其余要求对应已完成、疑点已有裁定，不追加一轮全量review，不重开历史审批门。本报告不改写既有PM验收或宣布W005已经开始。

## 附录：REQ-01 可移植复现

以下为本轮实际执行的完整脚本（SHA-256见§5）。在被审提交保存为仓库外的 `probe.py`，运行 `python -B probe.py <checkout绝对路径> <不存在的输出目录>`。只修改该输出目录的fixture副本，不修改checkout。正常几何正确性另有独立检查；此脚本使用现有spec/oracle提供稳定对象标识与CDL语义，以隔离helper消费精确raw值的行为，不将其作为另一份独立几何oracle。

```python
"""W004 scoped precision reproducer; never imports KLayout or changes checkout.

Usage: python -B probe.py /absolute/path/to/Layauto /absolute/empty/output
This executes check_body, then the unchanged raw_answers function extracted
from its source AST to show the normal-verifier guard. It does not execute
witness or the complete verifier and does not claim product runtime coverage.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from fractions import Fraction

repo = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
assert not out.exists(), "Output must not exist"
sys.dont_write_bytecode = True
sys.path.insert(0, str(repo / 'tests/support'))
from w004_support import load_tech, bind_header, bindings, read, write
from w004_body import check_body
from w004_query import CAPS, normalize, verify_backlinks

fixture = repo / 'tests/fixtures/w003_m1'
shutil.copytree(fixture, out, ignore=shutil.ignore_patterns('failures'))
raw = out / 'query/raw/net_shapes_n_lo.txt'
original = raw.read_text()
assert original.count('1160 900\n960 900') == 1
raw.write_text(original.replace('1160 900\n960 900', '1160 901\n960 901'))
# Bind actual mutated raw bytes before reparsing. Normalized is comparison
# cache, outside the selected closure; it is regenerated from the new raw.
write(out / 'query/header.json', bind_header(out, read(out / 'query/header.json')))
normalized = normalize(out, 'net_regions')
write(out / 'query/normalized/net_regions.yaml', normalized)
bindings(out)

shapes = {x['id']: x for x in read(fixture / 'spec.json')['shapes']}
semantic = read(fixture / 'oracle.json')['semantic']
body_result = check_body(out, shapes, load_tech(out), semantic)
row = next(x for x in normalized['records']
           if x['derived_layer'] == 'toy_m1' and x['schematic_name'] == 'VSS')
assert row['bbox_nm']['x_max'] == {'numerator': '901', 'denominator': '20'}
assert shapes['MN']['bbox'] == [0, 48, 45, 58]
assert len(body_result) == 2

# Run the existing guard without importing the KLayout-dependent module.
source = repo / 'tests/support/w003_verify.py'
node = next(n for n in ast.parse(source.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'raw_answers')
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'))
normal_raw_result = raw_answers(fixture, read(fixture / 'spec.json'))
try:
    raw_answers(out, read(fixture / 'spec.json'))
except AssertionError:
    guard_result = 'AssertionError; integer-nm guard rejects before full verify check_body'
else:
    raise AssertionError('Expected upstream integer-nm guard rejection')

result = {
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    'python': sys.version.split()[0],
    'command': ['python', '-B', str(Path(__file__).resolve()), str(repo), str(out)],
    'mutation': 'only VSS raw rail x_max 900->901 (45->45.05nm); GDS unchanged; header/hash/cache rebound',
    'bindings': 'passed',
    'source_gds_unchanged': hashlib.sha256((fixture/'source.gds').read_bytes()).digest() == hashlib.sha256((out/'source.gds').read_bytes()).digest(),
    'actual_raw_bbox_nm': row['bbox_nm'],
    'local_rail_bbox_nm': shapes['MN']['bbox'],
    'check_body_result': body_result,
    'normal_raw_answers': normal_raw_result,
    'probe_raw_answers': guard_result,
    'witness_executed': False,
    'witness_limitation': 'KLayout unavailable; path to check_body reviewed in source only',
    'product_runtime': False,
}
write(out / 'probe-result.json', result)
print(json.dumps(result, indent=2))
```
