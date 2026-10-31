# W004 — W003 样本修订与验证

> 执行恢复补记：2026-10-31用户已在准备交付后正式派发本任务，D1=A、D2后置MR-040机制、D3保留三类检查及未消歧旧义务均已落定。下方“仅准备/待PM”是保留的交接历史；本轮实施与证据从[E3](#w004-execution)恢复，不重复收敛。最终任务阶段/验收及W003关闭仍归PM。

最终目标是将W003人工修改要求落实为可复现的新样本。**按用户最新指令，当前只收敛任务，尚不开始实际样本修改。** 讨论历史留在[MR-076及其原记录](W003/manual-verification.md#mr-076)；本任务是当前唯一修订准备入口，产品合同仍归[架构](../architecture.md)。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| 目标 / 依赖 | 承接[W003](W003-m1-fixture-contracts.md)人工核验遗留，形成可供后续M1 parser使用的修订版fixture、合同、独立答案与反例。W003保持待验收，完成后PM用同一套新版证据关闭两任务相应要求 |
| 授权 / 阶段 | 2026-10-31用户明确“在实际修改前还是先收敛任务”，并授权推送文档及修改prompt。**待准备：下一session仅任务收敛。** 此指令替代此前“已定项可直接修改”的安排；收敛结果交PM接收，后续明确启动后才实施 |
| 版本 | 准备基线为`codex/w003-manual-review@b41ba92940516ecadd26c64fc9fcb6829d21cbe1`，已含MR-076。本任务及入口随本轮文档提交保存；接手使用包含“仅任务收敛”的已发布提交，具体SHA以Git及交接回复为准 |
| 当前写入范围 | 本任务的方案/准备结果、独立准备review及必要恢复入口。正式fixture、support helper、既有样本合同/图/报告、架构与产品代码均只读；原人工决定及W003 E/R历史不得覆盖 |
| 后续拟修改范围 | 经收敛接收并明确启动后，再修改`tests/fixtures/`专用样本、`tests/support/w003_*`及必要专用辅助、`docs/tasks/W003/`受影响附件；范围和依赖在本次收敛中明确。沿用既有路径，不因编号批量搬迁 |
| 非目标 | 不实现`layauto_v2/` parser/runtime、完整grid/CSP/DTO/codec/CAS；不改架构、legacy或部署EDA/生产上传；不扩大真实PDK/工具能力承诺 |
| 架构依据 | §2.2、§3.4–3.6、§4.8、§5、§10.3/10.5、§11.14–11.15、§12.1–12.8；按修改读取原条款与两侧合同，不以本表替代原文 |
| 分工 | 下一session负责只读调查和任务收敛，独立reviewer检查要求覆盖/边界；PM接收并安排后续实施。未来样本由一名执行者串行集成，再做新版技术review；新关键语义按协作规则§5处理 |

以下为待收敛的修订要求输入；本表不授权本阶段修改样本，也不表示验收已经执行。

| ID | 应改成什么 / 关键限制 | 后续样本验收证据 | 来源 |
| --- | --- | --- | --- |
| R1 | 补齐单位/尺寸来源链、尺寸—规则—适用条件对应；tech按唯一owner分类并实际被辅助消费。文件数不冻结，缺规则不杜撰生产数值 | 来源/字段映射、精确单位核对、规则正反例；无隐藏重复tech权威 | MR-002/004 |
| R2 | 正常例移除LB/CUTB及R08/R09，CUT分片、同标签/同格不合并迁专例；body按专门tapcell场景修订，不要求每个逻辑cell内有BTAP | 新图/坐标/端子/连接/规则及独立答案；body方案先明确证据/作用域，新输入解释经必要决定后集成；C22相应迁移 | MR-020/046 |
| R3 | 用基于legacy格式资料的单一Calibre-like方言替换W003_QUERY；normalized具名、可读，保留原文定位、lexeme、精确值、unit/quality和hash | raw→normalized字段核对、header/closure实际文件清单；撤下旧方言active入口，不加转toy中间层，继续标synthetic | MR-030.2/034 |
| R4 | 32×16仅为人为测试分格，coordinate/component引用不暗示完整runtime；明确Virtuoso检查范围后统一身份或映射；修正L/channel length及样本classification措辞 | 合同/样张/策略/报告一致；deferred、coverage none、requires_review不变；无新增完整坐标设计门槛 | MR-051/052、074-Q1、001-Q1/039 |
| R5 | 同步所有受影响输入、答案、反例、helper、图、记录、报告、引用/hash | C01–C22逐项迁移表；正常与8类失败样张引用自洽；原F1/F2保证保留；新版数量重新计算，不沿用旧44/10/6作为答案 | MR-076、W003 R1 |

## 方案与决定（执行准备，PM接收）

<a id="prep-20261031"></a>
### 本轮交付范围与状态（2026-10-31）

本节为本次执行准备结果，**仅任务收敛，交PM接收；没有开始样本修改**。下述“验收”均为后续方法/预期，不是新版运行结果。已定方向按原MR执行，不再询问是否分类tech、拆分孤岛、使用专门tapcell或替换为单一raw方言。具体body输入和检查范围候选仍须决定；不借旧P7 prompt或历史提交授权启动实施。

恢复实物为 `/workspace/Layauto`、`work@da55ca656e5e38caba1e7f47483137c68c044907`，包含 `766df17` 的“仅任务收敛”版本，且与该提交相比仓库内容无差异。启动时staged/unstaged/untracked均为空。只读 `git ls-remote origin refs/heads/main refs/heads/codex/w003-manual-review` 确认main为同一SHA，旧审核分支未返回；因此使用已有完整checkout，不回退到旧b41ba92。原MR-076、W003 E/R和旧材料身份保留，Mac临时附件未取得或重验。

路径简称：**F**＝[tests/fixtures/w003_m1](../../tests/fixtures/w003_m1/)，**H**＝[tests/support](../../tests/support/)，**D**＝[docs/tasks/W003](W003/)。原MR见[人工清单](W003/manual-verification.md)，原review F1/F2见[W003 R1](W003-m1-fixture-contracts.md)。本轮只读核对了这些实物、对应架构原文及legacy格式资料；辅助源码的可见限制也纳入下方验收计划。

### 1. 精简要求表

| ID / 状态 | 改成什么与关键限制 | 来源 / 架构 | 后续可接收证据 |
| --- | --- | --- | --- |
| R1a 已定 | 单位形成raw UNITS/XY→versioned nominal依据→exact binding→canonical tick/可表示性链；区分source DBU、canonical tick、合法工艺网格和索引格。1nm是有出处的toy选值，GCD不产生单位、工艺规则或产品默认 | MR-002.1；§2.2、§12.5 | 原bytes/lexeme、decoded rational、nominal/delta/bound、版本与原XY回链；缺来源/冲突/不可表示的见证 |
| R1b 已定 | 每项关键尺寸列实际值、设计选值、规则限值/精确值、方向/单位/条件、出处版本、模型/PCell/track关系和独立判据；分类材料必须实际被辅助消费且每类事实只有一个owner | MR-002.2/004及MR-023纠正；§4.8、§12.2–12.5 | 旧字段→owner→消费者表、尺寸/规则对应表及适用正反例。FIN间隙8=10−2不是已有最小间距规则；gate x尺寸4/L不等于已有gate spacing规则。无来源项列缺口，不杜撰生产数值 |
| R2a 已定 | 正常例移除LB/CUTB和R08/R09，CUT分片、同标签/同格不合并及孤岛披露移专例；MARK保留原决定 | MR-020、021/022；§3.5–3.6、§12.8 | 正常/专例独立几何、fragment、component、规则适用集合及图；保留负例目的，新数量独立重算 |
| R2b 方向已定，具体输入待D1 | 逻辑cell不以本地BTAP为body成立前提；用获批tapcell上下文支持body解释。有序D/G/S/B及MN0.B=VSS、MP0.B=VDD目标语义保留；不能凭网名造物理边，也不能用未运行LVS援引冻结豁免 | MR-046；§3.6、§4.8 | 本地physical components与context-supported body association两张答案；输入绑定、每段几何关系、T04/T05/T08适用范围与C22新见证 |
| R3 已定，具体格式方案须可核查 | 以legacy保存的格式描述为依据，用一套versioned Calibre-like方言替换W003_QUERY；normalized主体具名可读，保留raw位置/lexeme/exact值/unit/precision/quality/hash。四capability不固定四文件，不加转toy层，不引入legacy runtime | MR-030.2/034；§2.2、§5、§11.14–11.15、§12.6/12.8 | 多输入关联清单、独立normalized答案、精确坐标换算、完整raw清单及C02–05/F2迁移；旧toy active入口撤下，历史记录保留；仍为synthetic而非真实capture |
| R4a 已定范围纠正 | 32×16只解释人为测试分格和同格不连通目的，随孤岛专例迁移；coordinate/component引用明确example_only及不完整snapshot，不补完整网格/CSP/DTO/codec/CAS | MR-051经052收窄；§3.4–3.5、§12.3 | 专例假设/几何期望、coordinate_ref与component refs可解析且范围一致；完整坐标模型明确留后续Stage 2 |
| R4b 问题待修，范围待D3；措辞为建议 | Virtuoso policy/check/报告身份与范围一致；建议L改称channel length、classification只说明synthetic样张性质，不含review进度。后两项为子PM措辞建议，非用户新增语义决定 | MR-074-Q1、001-Q1/039；§10.3/10.5 | D3范围表、完整ID映射及人机报告对账；deferred/none/requires_review、未执行状态不变；不改L/W数值或模型 |
| R5 已定 | 同步全部受影响输入/独立答案/22原反例目的/helper/图/记录/报告/引用/hash；保留F1/F2，不把旧44形状、10边、6分量、75文件当新版答案 | MR-076、W003 E4/R1；§10.5–10.6、§12.8 | 第4节逐项证据及完整版本身份，正常和8类失败样张同源；辅助检查、未来产品结果与人工判断分别记录 |

正式parser、通用loader/算子注册、真实工具获取、产品失败管线及生产签核均属后续实现；不能为完成本表提前实现，也不能用“后续实现”取消本轮样本来源和独立答案义务。

### 2. 范围、数据依赖与集成责任

| 文件/数据（现有实际路径） | 后续变更与消费者 | 依赖 / 集成次序 |
| --- | --- | --- |
| F/`tech.json`全体字段、`site_config.yaml.tech_ref` | 分类为bundle引用、规则、drawn层、derived映射、物理profile、格式/单位等明确owner；分类导航和辅助读取同一来源 | D2建议沿用现有policy入口即可推进。具体文件名/数量/schema不冻结；body部分等待D1，最终引用重绑在分类完成后 |
| F/`spec.json`、`oracle.json`、`source.gds`、`source.cdl`、`target.cdl`、`expected/*` | R2几何/端子/body、fragment/components/edges/non_edges、规则集合、单位provenance、source/expected语义；孤岛专例另有独立输入和答案 | 正常/孤岛拆分方向已定；body、最终计数和T04/T05/T08依D1。CDL语义不因重绑任意改写；先手写独立答案，再生成/读回 |
| F/`query/raw/*`、`query/normalized/*`、`query/header.json`，`spec.json`四类evidence | R3方言、nXref/NET NAMES关联、具名坐标/原文回链，`header.raw/closure/top_identities/hierarchy_mode/geometry_unit_contract` | 格式调查与坐标换算可先准备；最终文件清单取决于R2几何、分类路径及D1上下文。新增设计事实仅作evidence输入，不塞入tech/site覆盖字段 |
| F/`failures/cases.json`及全部`failures/*` | 每例replacement/remove列表、坏输入、header/cache/closure及错误见证；C22原为删`operators["body/1"]` | 依新正常底座和D1；按第4节逐例应用，不能用旧目录名或旧19次循环计数代替迁移证据 |
| H/`w003_generate.py`、`w003_verify.py`、`w003_plot.py`、`w003_record_examples.py` | 实际读取分类资料、正常/专例、raw及记录/报告依赖；移除旧方言active路径及旧固定答案 | 输入/独立答案先确定；生成与核验不能共享唯一正确性依据。现verify直接访问CUTB、固定44等，必须适配场景，不能删断言凑通过 |
| F/`export_policy.json`、`validation_policy.json`、`limitations.json`；D/`examples/{schema,records,failures,report.expected}.json`、`examples/report.expected.md` | policy与检查ID、实际文件refs/JSON pointers/hash、request digest、scope披露、正常/8失败与人机报告；expected layout引用同步 | policy机制依D2（推荐后置），Virtuoso依D3，body/孤岛计数依D1/R2；最后统一生成或更新并核验，不并发重写 |
| F/`README.md`；D/`README.md`、`contracts.md`、`handoff.md`、`fixture-layout.png` | 阅读导航、来源/尺寸解释、单一方言/能力范围、图与未来实现边界 | 跟随最终实物，L/classification建议只作措辞修正。W003原E/R、MR人工历史不改写，受影响人工结论由PM另记 |

**tech归属需落实到所有现有键，以下为职责映射，不是批准的物理文件数：**

| 当前字段 | 唯一owner / 引用关系 |
| --- | --- |
| `schema_version/profile_id/classification/production_technology` | bundle身份/来源；入口引用分类内容，不留隐藏的大JSON真源 |
| `rules/mandatory_rule_policy` | 按规则实质分类：T05 enclosure、T06/T07 spacing归尺寸规则；T01边界、T02阵列/profile、T03提取、T04 body/enclosure、T08连接、T09保真、T10覆盖分别归相关合同并保留mandatory引用，不能统称DRC |
| `layers/derived_registry/coordinate_projection` | drawn层与lifecycle policy、derived映射分别拥有；annotation容差从单位块归derived mapping。粗分格仅专例测试说明，不成为runtime coordinate模型 |
| `unit_scale_contract/geometry_capability/cdl_dialect/limits` | 单位/格式来源及输入子集；CDL模型语义指向物理profile，语法不重复模型/单位权威 |
| `fin_count_profile/device_extraction_contract/operators/capabilities/required_operator_refs` | 物理profile及具名算子合同；FIN width/pitch/offset单一来源，规则按引用消费；body待D1。固定实现不变量无需全部变成配置开关 |

**写入责任：**本轮由执行准备主代理统一写W004及必要恢复补记；调查代理只读。后续实施由PM指定一名集成人串行管理F/H/D共享文件，尤其header、spec/oracle、cases及records/report，最后统一重绑；独立reviewer不承担样本实现。body决定前不冻结相关图/边/统计；分类文件与policy决定前不冻结最终closure。PM拥有阶段/人工决定，reviewer拥有新增review结论。

### 3. 最少待决项与推荐（交PM处理，均非已批准方案）

#### D1：body上下文的输入与作用域

**推荐评审候选A：本地flat逻辑cell＋显式只读synthetic外部几何上下文。** 正常cell移除本地TN/TP；本地BN/BP不再假装经本地tap接rail。关系示意：

```text
本地：MN0.B → BN；BN 与 MN 是不同的本地 physical components
上下文：BN —同类型边接触— BN.ext —TN.ext— MN.ext —边接续— MN
目标比较：上述几何链支持 B 到 VSS 的关联，不能由 VSS 名称生成链
P侧同理：MP0.B → BP → BP.ext → TP.ext → MP.ext → MP → VDD
```

P7可用于审查的最小数值示意仍只是候选：N/P body延伸分别为 `[-20,0,0,90]` / `[-20,100,0,200]` nm，rail延伸为 `[-20,48,0,58]` / `[-20,148,0,158]`，tap为 `[-12,50,-8,54]` / `[-12,150,-8,154]`。本地BN/BP从x=0开始，MN/MP亦在x=0接续。正长度同类型边接触能否导通、tap类型、两侧唯一匹配及包围必须成为明确toy语义和独立判据；这些坐标不是PDK规则或已批准样本。

| 待明确的最小合同 | 候选A的表达与影响 |
| --- | --- |
| 来源/绑定 | 单独evidence输入选择；记录source GDS实际hash、top、body/frame/rail对象身份、单位/坐标框架及boundary接续位置、profile/operator版本、上下文实际文件hash、synthetic作者/来源。header依赖闭包和F1 request选择摘要纳入全部叶子文件；不将具体bbox/连接答案藏进tech/site |
| scope与答案 | 分列本地physical graph和context-supported association；逐段给几何边、输入位置、算子及适用域。扩展context不写回本地GDS、不冒充本地edge；source/expected和报告明确哪些对象属于导出本地范围、哪些仅为支持上下文 |
| 正常/失败 | 正常无本地tap仍可在所选toy上下文成立；缺必需context/算子、错source绑定、错body类型、tap包围不足、接错rail分别有见证。C22选“缺必需支持”保留P阶段目的；几何关系不成立另列相应解释/验证阶段，不统用旧错误码 |
| 规则与能力 | T04移除“每cell显式BTAP到rail”条件，但类型/enclosure等按新profile保留；T05本地与外部connector scope分列；T08连接答案区分两域。`body_complete_for_toy`只在独立证明新scope后声明；`production_matched_body_evidence=false`、LVS not_run不变 |
| flat输入影响 | 主GDS继续`one_reachable_flat_cell`；当前拒绝additional_cell/SREF/AREF，不能直接塞层级tapcell。A虽不改主GDS层级，仍新增一类输入和解释scope；§3.6允许tech-dependent body graph不等于已批准此schema。若需架构合同改变，先交PM，不以fixture静默引入 |

**替代B：单一flat整体测试窗口含逻辑cell与tap区域。** 减少外置上下文表达，但改变top/frame、输入身份、T01及规则scope，也弱化“逻辑cell不含tap”的直观边界；同样需PM决定。**当前不可选**“仅删除TN/TP后凭CDL标签连边”或“声称baseline LVS冻结”：前者无物理证据，后者本轮无真实LVS证据。

交PM的决定点只有：采用A还是B及其scope/绑定/失败预期。tapcell方向不再提问。A的具体字段名和最终坐标可在获准范围内细化，不能先写fixture再倒推批准。

#### D2：MR-040配置精简是否纳入

**推荐明确后置MR-040机制变更，本轮完成MR-004分类。** 保留site、export/validation policy、limitations现有入口，只调整分类引用与必要样本内容；不新增默认值/override/profile构造机制。已有 `site.outputs.core/directory` 与 `export_policy.required_artifacts/output_directory` 重复，在样本核验中要求一致、披露重复及冲突，不擅设优先级或以一处覆盖另一处；唯一外部选择→派生有效策略的机制留MR-040后续决定。

若本轮采纳精简，最低决定包须先列旧字段→保留输入/固定profile/派生结果/删除重复的映射、版本/默认来源和冲突规则，说明F1/closure/报告迁移；required错误reject、deferred不算pass、精确单位和完整产物义务不能删除。该选项会扩大配置语义范围，当前不推荐。后置不阻塞body/格式调查或已定分类；不能因未决定MR-040而继续保留隐藏tech权威。

#### D3：Virtuoso检查身份与实际范围

**推荐候选：统一为 `virtuoso_dry_run`，明确表示未来真实Virtuoso/SKILL dry-run的shape locate、exact匹配、歧义/缺失及return-code检查（§10.3/10.5）。** 不含apply，也不把它当独立下游GDS打开/回读。

| 现有位置/名称 | 推荐候选的对应关系 |
| --- | --- |
| F/`validation_policy.json.deferred`、D/`examples/report.expected.json.deferred`及人读报告的`virtuoso_readback` | 只有PM接受上述scope后，统一到`virtuoso_dry_run`并改说明；不是现有同义别名证明 |
| D/`examples/records.json` ValidationResult及H/`w003_record_examples.py`的`virtuoso_dry_run` | 与同一scope及policy对应；合同、失败样张/schema涉及的refs/断言同步核对 |
| 下游工具打开GDS/readback | 若PM实际需要此能力，另设独立检查及输入/答案范围，不能无依据映射为dry-run；不把新工具执行加入本轮 |
| Calibre名称关联 | 同时核对policy/report的`real_calibre_drc/lvs`与记录的`calibre_drc/lvs`映射，显式说明真实工具scope，避免只修Virtuoso留下无说明名称关系 |

两方案均保持deferred、coverage none、requires_review、null执行时间/return code及真实工具未运行。此次只决定样张表达，不安装/调用Virtuoso。若最终仅需下游readback而非dry-run，PM需明确选定其含义后再修订；不能“改个名字即关闭”。

#### 已定R3的最小格式示意（不新增选择门槛）

实际资料位于 `legacy_mvp/dummy/fixtures/{iXref.temp,nXref.temp,net_names.txt,device_info_M0.txt,device_info_M1.txt,net_shapes_*.txt}`，解释线索在 `legacy_mvp/io_adapters/calibre_query.py`。这些是合成文本/格式描述，真实Calibre版本仍未知。xref的 `# SVDB: End of header.` 仅结束header，不能当文件终止符；有 `END OF RESPONSE` 的NET NAMES/DEVICE INFO/NET SHAPES可承载C02。

候选展示：按资料的 `(y,x)` 和 `µm=整数/precision`，precision=20000时raw `400 1160` 对应 `y=20nm, x=58nm`；normalized主体给具名exact坐标，同时保留两段lexeme、precision/unit来源、文件/行/token、header/hash。完整polygon顶点和quality保留，只有确证矩形的profile才可给exact rectangle。nXref与NET NAMES按名称关联到后者顺序索引；索引为query-run scoped opaque身份，不为保留旧007伪造字段。最终方言声明版本、完整性/数量/未知结构处理和独立答案；不照搬legacy浮点取整、PMOS测试swap、旧top或便利JSON。

### 4. 后续验收清单（本阶段未执行）

| 检查 | 方法 / 必须保存的证据 / 通过边界 |
| --- | --- |
| V1 独立答案与单位 | 先手写所选场景的坐标/端子/body/组件/规则适用表；独立reviewer用不共享生成器算法的integer/Fraction计算及独立GDS读回核对source/expected语义、REAL8/nominal/bound/原XY、完整CDL有序pins/globals/models/端子/参数。单位writer共享部分如实披露；不能只靠同源generator/verifier或旧golden |
| V2 raw同源与闭包 | 从每个具名normalized字段回到真实raw文件/位置/lexeme/exact值/unit/quality；独立核对多输入join。枚举实际tech分类、policy、body和source dependencies，逐叶重算bytes hash及canonical closure；所有typed refs/JSON pointers可解析。hash正确不等于几何/语义正确 |
| V3 全22目的迁移 | 在独立目录复制新正常底座，严格按每例replacement_files/remove_files应用；逐例登记实际路径、见证、预期issue/阶段、绑定状态和实际结果。故意错误只限声明位置；不能让意外hash错误遮住目标缺陷。孤岛专例/body额外见证不替代原22目的 |
| V4 正常与8失败样张 | 正常仍为expected no_change、空ECO链，核心对象size/实际bytes hash、run/snapshot/manifest/结果引用一致；逐项核对下表8类非法/合法组合。机器报告所有input/limitations refs也遍历，人读报告按数量、scope、check映射、限制和disposition逐项对照 |
| V5 F1保证 | 完整pre-context descriptor含operation、proposed run/lineage、starting head、idempotency key及全部实际input/raw/config/policy选择/bytes；分类和新增body输入均纳入，不提前放canonical context IDs。独立重算canonical SHA-256；分别改变run/head/lineage/所选文件bytes须改变摘要，沿用旧摘要须拒绝，不沿用旧13 refs数量 |
| V6 F2保证 | 读取新方言真实缺终止结构的坏raw，独立确认坏点与bytes hash；其重绑header→独立fixture-read ToolRun→ParseResult→StageFailure/localized→failure RunRecord completed refs全链同源。不能引用正常raw或继续用旧END W003_QUERY断言 |
| V7 再生成、图及身份 | 实施获准后才在新目录运行生成/绘图，比较再生成全部文件并对图核坐标；byte-clean只证明重复性。保存被测HEAD、相关完整snapshot/binary patch（含untracked）、SHA-256清单、命令/环境/stdout/stderr及独立review结果；历史原文不覆盖，未运行项单列 |

现有H/`w003_verify.py`固定旧tech入口、W003_QUERY、CUTB及部分数量/阈值；overlay循环用文件回退，不能替代真正按replacement/remove应用。H/`w003_record_examples.py`只遍历records/failures，机器报告仅检查少量标记、空链和disposition，未遍历其input/limitations refs，也未检查人读报告；新版V2/V4须补齐这些样本核验路径，不能降低断言来适配输入。C08/C10等当前只证明见证存在，不等于执行产品typed failure。

#### C01–C22目的迁移

P＝pre_context，S＝sealed_no_publication，E＝export，沿用现有目的/阶段，不发布产品enum。**B**＝新底座上重做overlay、更新配套header/closure/cache/hash；**D**＝仅保留指定故意缺陷，其余正确。C02–05无法合法归一化的raw须删除对应旧cache，不伪造normalized。

| 原ID / case | 保留目的及新见证 | 绑定 / 阶段 |
| --- | --- | --- |
| C01 unit_mismatch | GDS编码单位与所选声明冲突，先排除意外hash错 | B / P |
| C02 missing_terminator | 新方言确有终止结构的响应删必需结束标记，更新F2链；不向xref杜撰END | B / P |
| C03 wrong_count | 新方言真实数量声明与实际记录数不符，不机械搬COUNT 5 | B / P |
| C04 dialect_drift | 新方言不支持的几何token/结构，不能默认为精确矩形 | B / P |
| C05 unknown_unit | 新raw或其规定绑定位置的未知单位/precision不能确立单位，不造无关字段 | B / P |
| C06 raw_byte_drift | 改新raw真实bytes，故意不改对应header/raw hash | D：raw hash / P |
| C07 header_top_mismatch | 仅令header top与实际输入不符 | D：top / P |
| C08 mapping_many_to_one | 两layout device指向同一schematic device，raw/normalized同步 | B / P |
| C09 multifinger | 实际CDL NF改2，保留不支持finger count目的 | B / P |
| C10 device_reduction | 增加第三layout对应以要求归并，与C08分别记录目的 | B / P |
| C11 cdl_expression | NFIN等价表达式仍不属于支持语法，不能只求值比较 | B / P |
| C12 cdl_include | 合成.INCLUDE指令仍不支持，不引入私有文件 | B / P |
| C13 unsupported_target | 只变固定target轴L，FIN目标相同也不得判no_change | B / S |
| C14 count_correct_rule_wrong | 新几何下计数正确但M1 spacing违反；独立测量，更新GDS/region，不盲抄旧坐标 | B / S |
| C15 via_enclosure | 新connector/rail集合中的真实包围不足，独立计算 | B / S |
| C16 extraction_mismatch | 实际crossing与CDL声明不同，raw/normalized与改变后的几何同源 | B / S |
| C17 gds_text | 实际加入不支持TEXT，显式拒绝而非丢弃 | B / P |
| C18 gds_nonrectangle | 真实非矩形不能用bbox冒充lossless | B / P |
| C19 output_nonrepresentable | 新坐标至少一项输出tick换算非整数；先证明源单位合法，不round | B / E |
| C20 output_overflow | 换算均为整数但至少一项超signed 32-bit；不截断 | B / E |
| C21 normalized_cache_drift | raw/header正确，仅具名cache字段与raw不符 | D：cache / P |
| C22 missing_body_operator | 按D1选缺必需operator/context/evidence支持；无本地BTAP本身不是错，具体路径/issue随决定 | B / P，依D1 |

每例应有“旧目的→新替换/删除路径→见证→issue/阶段→实际检查与证据”记录。当前19个非故意绑定缺陷目的与3个D类目的都要重新证明；新总数可以增加，原目的不可消失。样本辅助可证明见证、精确关系和绑定闭合；`reject/0 ECO/无正常export manifest`仍为未来产品断言，未运行产品就不能报告管线通过。

#### 正常/失败报告的8类逐项检查

| 变体 | 后续样张必须表达的边界 |
| --- | --- |
| pre_context | 真实坏输入→最小failure RunRecord/StageFailure/completed audits；无未建立canonical context、ECO、正常geometry/Manifest/ValidationResult |
| sealed_no_publication | 可保留稳定baseline，无ECO/正常几何导出；diagnostic report不冒充正常export |
| run_record_freeze | 唯一允许无RunRecord的例外，Stage5Closure明示freeze failure；不编造记录或正常export/validation |
| export_failure | 保留frozen no_change RunRecord/snapshot，可有staging/orphan；核心不全无成功Manifest/正常validation |
| check_fail | 检查已执行并发现fail，required→reject，不用golden覆盖 |
| check_error | 执行/解析error与fail/pass区分，required→reject |
| reporting_failure | 既有checks不改，加ReportingResult/StageFailure；required报告失败→reject |
| terminal_storage_failure | best-effort诊断，不虚构terminal pointer/accept或持久恢复证明 |

### 5. 实施顺序、停止点与下一角色

| 顺序 | 最小动作 | 进入条件 / 停止点 |
| --- | --- | --- |
| 0 本轮 | 完成上述五项、文档检查、独立准备review和完整工作区身份交回 | **到交PM即停止；没有样本写入授权** |
| 1 PM接收 | 判定D1 body输入/scope、D2明确后置或采纳、D3检查含义；接收措辞建议及后续实施范围 | 准备review不替代PM接收/必要用户语义决定；PM随后明确启动，不能由执行者自动转阶段 |
| 2 获准后的来源/答案准备 | 先分类owner/单位/尺寸来源表、单一方言明细及独立答案；再确定正常/孤岛/body各scope | 未定D1时只推进不依赖body的授权部分；body、最终组合计数与C22停止。D2后置即可保持既有policy边界 |
| 3 获准后的串行样本集成 | 更新正常/专例、分类实际消费者、raw/normalized及全22 overlay；按实际文件闭包重绑 | body和分类路径确定后才冻结header/request/引用；保留旧人工决定与E/R正文 |
| 4 组合核验与新版review | V1–V7、正常/8失败人机报告、F1/F2、图和完整身份；独立review及受影响人工结论 | 未决语义、独立答案不成立或错误被意外binding遮住时暂停相关部分交PM，不扩架构/产品 |
| 5 PM后续接收 | 以同一新版证据接收W004并关闭W003相应遗留，之后才派M1 parser/输入绑定 | 收敛交回不等于W004最终验收；本session不执行第1–5步 |

本次没有剩余只读调查阻塞。实际修订仍有D1、D2、D3选择及PM启动门槛；需改变架构/输入承诺时由PM处理。具体下一角色为**PM接收执行准备**，不是样本执行者。历史文档的提交推送授权不延伸到本session；本次未授权commit/push/merge/删分支，也不更改或发布云环境配置。

## 执行结果（执行）

### E1. 本轮准备交回（2026-10-31）

五项结果已写入上方第1–5节，状态为**准备材料已形成，待PM接收；样本未修改，W004未最终验收**。实际版本与初始干净状态见本节顶部恢复记录。调查由主执行准备代理统一集成，`r1_r2_sources`、`r3_r4_sources`、`r5_acceptance`仅做只读来源/依赖调查；最终准备review另由未参与编写者执行并记录下节。

本轮修改集限本文件及 `docs/current-work.md` 的执行准备恢复补记；不改PM历史决定、W003原E/R、人工清单、fixture/helper/既有附件、架构、产品或legacy。历史“下一session尚待收敛”是当时PM记录，本次恢复应从E1及新增review段交PM，不再次启动准备prompt或实际修订。

检查限 `git diff --check`、修改范围/原文件保留、Markdown相对链接/锚点、表格列数及恢复指向；具体结果与受审材料身份在下节及交回证据中记录。未运行生成器、绘图、pytest/完整回归、样本校验器、产品或EDA；不把此前环境初始化结果用于新版验收。剩余决定为D1–D3，必要材料已在第3节给出，不要求本session用户即时答复。

本机交回材料存于 `/workspace/w004-preparation-20261031/`：受审/最终两份文档snapshot、相对上述HEAD的binary patch、SHA-256清单和文档检查记录；只用于本实例交回，未提交/推送，不能假定另一主机可读取。跨主机前由获授权者保存这组完整材料，不能只传HEAD或旧Mac临时路径。证据身份不要求正文包含自身最终hash。

### E2. 提交推送交接补记（2026-10-31）

用户在本次交接session明确授权将上述收敛成果提交并推送到`codex/w004-task-convergence`，仅包括本文件和`docs/current-work.md`。该授权替代前次准备session的“未授权commit/push”状态，不扩展为合并main、修改样本、运行生成器或启动实际修订。发布基线仍为`da55ca656e5e38caba1e7f47483137c68c044907`；创建分支前本地分支列表及远端`ls-remote`均未发现同名分支。使用`LucianoHoult@users.noreply.github.com`作为author/committer邮箱，普通推送，不强推。最终提交SHA及推送成功事实以交接回复和远端分支核验为准，本段不自指尚未生成的commit。

**PM接收所需的事实与身份随这两份文档保存：**五项准备交付在第1–5节；独立准备review的原结论、方法、来源范围和未执行限制完整保留在RP1，结论为0项必须修正findings。其受审版本是追加RP1前的完整两文档，基线与SHA-256如下；不能把后加的review/发布补记冒充已经受审的正文。

| 材料身份 | W004 SHA-256 | current-work SHA-256 |
| --- | --- | --- |
| RP1受审snapshot，基线da55ca6上的准备交付 | `57d03ade619cb9ceb8acfa09053e22a40e48700bc0efc4c3661baa38c3c3de8a` | `5b6f7b46c37351cf05fe8c93753e70688b74b30b8f75d2ac0f823aacab4c17dd` |
| 追加RP1后的上一轮最终交回snapshot，本次发布补记之前 | `67cbb8529a0a2817ca1bf25c2b18413516f9ed705118053f1c496d0877b3e511` | `5b6f7b46c37351cf05fe8c93753e70688b74b30b8f75d2ac0f823aacab4c17dd` |

本次恢复已逐项重算本地`review-input/SHA256SUMS.json`的4个条目和`final/SHA256SUMS.json`的5个条目，确认两工作区文档与上一轮final snapshot逐字节一致。上一轮最终检查为：25个相对链接/锚点、12张表、22个迁移目的、`git diff --check`及受保护文件无改动检查通过；以`git show <base>:<path>`取得两份基线原文，在普通临时目录应用binary patch后与snapshot逐字节相等，未创建checkout/worktree。上一轮final/full.patch的SHA-256为`a453f9021734f658963b04edcdd602d389f6c6c0a11b94916ad7eba46a475def`。初检11张表与最终12张表的差异仅来自RP1表格，不是样本数量变化。

这些事实摘要和身份纳入Git；`/workspace/w004-preparation-20261031/`及旧Mac临时证据包没有随本次推送上传，不能声称PM另一主机已能读取附件。若需仅凭本提交恢复RP1受审文档，可按完整标题边界删除本E2整节和RP1整节（保留各自后续标题），并从current-work删除“发布交接恢复补记”整节；所得UTF-8原文应匹配上表第一行。保留E1、原review前导段及其他历史正文，不重排空行。发布补记不改变第1–5节方案、RP1结论或任何已定/候选状态。

仍待PM决定D1 body上下文的输入/scope与绑定、D2是否明确后置MR-040、D3 Virtuoso检查范围/身份；推荐和具体示意见第3节。此次只做文档diff/身份/链接/恢复检查及Git发布，未运行fixture/helper、生成器、pytest、产品或EDA；未新增新版样本验证结论，下一角色仍为PM核验接收准备成果。


<a id="w004-execution"></a>
### E3. 正式派发后的样本执行交回（2026-10-31）

**授权与恢复。** 本session用户明确以执行角色完成R1–R5/V1–V7，已接收五项准备交付并给定D1=A、D2、D3；因此历史“仅准备”不是本轮停止点。初始`/workspace/Layauto`为`work@da55ca6`，staged/untracked为空，unstaged为W004/current-work两份准备文档。先完整备份到`/workspace/work/w004/initial/`。Git CLI当时代理连接失败，GitHub连接器读到指定9f6735d与两份原文，核对blob、tree和commit SHA均精确相同，且现有修改为发布文件的完整保留子集；恢复指定`codex/w004-task-convergence@9f6735dcede8e8b2135f89ff10f079a752ed758b`。没有新建实现commit或推送、合并main、删分支；本轮提交/推送没有新增授权。

**实物。** 沿用F/H/D路径；主执行者串行集成全部共享文件。实现前`independent_answers`以源坐标和整数/Fraction推导独立答案，`dialect_sources`只读legacy格式资料，两者不参与最终审阅。正常40个本地图形、14有效导体、8本地connector边、6本地分量；BN/BP分别独立，外部六形状通过2条独立context association支持有序B语义。LB/CUTB/R08/R09及同标签同格目的迁至单独`special/cut_islands`（4 drawn、3有效片段/分量、0边）。[新导航](W003/README.md)、[来源表](../../tests/fixtures/w003_m1/sources.json)、[迁移/覆盖与两域图](W003/revision-evidence.md)、[合同](W003/contracts.md)及[人机报告](W003/examples/report.expected.md)已同步。

**D1–D3落地。** `body/context.json`显式绑定source bytes、top、FRAME/本地body/rail对象、单位与坐标框架、profile/operator、来源及synthetic限制；header closure与F1 request纳入该输入及全部技术叶。外部图形不导出、不并入local graph；接续长度90/100及10/10 nm、tap body/rail最小包围8/2 nm、类型/唯一匹配及目标rail分别核验。T04/T05/T08使用新版context作用域和版本，C22保留“缺必需body算子”目的，另7项body失败见证；无本地BTAP本身合法。tech六owner实际消费，规则/模型/单位无隐藏重复配置权威。site/policy/limitations入口保持，重复outputs不一致reject，未实现MR-040新机制。D3完整“身份—输入—证明—状态—原义务去向”表由validation policy拥有并进入人机报告；production downstream open/syntax、Virtuoso/SKILL dry-run与本地语义读回分项，旧virtuoso_readback未消歧义务明确保留，MR-074-Q1待PM关闭。

**已执行验证。** Python 3.12.14，KLayout 0.30.12；独立review另用gdstk 1.0.2。命令、环境覆写及stdout/stderr保存在完整证据包`validation/`。辅助检查实测：116个fixture文件、9raw→4capabilities记录2/4/2/8、558处字段回链、17个实际closure叶、27个F1输入路径；20正常记录、8失败变体、133处record/report文件引用、3核心artifact实际size/hash。29个failure overlay与9个配置/单位声明冲突变体均真实复制/替换/删除/重绑后检查；未用意外hash错误覆盖目标缺陷。F1逐operation/run/head/lineage/key及27个实际文件bytes改变证明摘要敏感，旧摘要拒绝；共66个非法记录/摘要组合检查。F2坏DEVICE INFO缺END OF RESPONSE，其header→独立读取回执→ParseResult→StageFailure定位→failure RunRecord completed链同源。GDS完整语义/REAL8/nominal/bound/原XY字节位置、CDL全字段、JSON范围/组件、T01–T10和图逐项核对。独立目录重生成116文件、图及20/8记录/人机报告逐字节一致，可重复性与正确性分别报告。

**独立review与修复。** 未参与实现的`independent_review`及`raw_independent_review`对冻结snapshot开展独立stream/CDL/integer/Fraction/多输入raw核验，未import生成器作为答案。初审IR1–IR5指出owner消费未完整、export旧profile、错rail见证混入异型body重叠、query单位/quality声明冲突未拒绝、DEVICE INFO缺数字type；原finding与复现脚本完整保留。已修复：实际消费或显式核验固定owner合同，增加9类实际声明冲突见证，补opaque数字type和owner回链，纠正profile、升级T04/T05/T08版本，错rail改为单一目标rail冲突并检查外部异型body不重叠。复核结论由reviewer另记，不由执行者代写。

**身份与未运行。** 受审最终实现快照位于`/workspace/work/w004/review-r3/`，完整封包保存在`/workspace/work/w004/artifacts/W004-delivery.tar.gz`（本云环境无法创建线程指定的`/codex/browser/projectless/.../output`展示目录；并非上传或Git发布，跨主机时须携带该包），含完整相关snapshot、相对9f6735d的binary patch（修改/新增/移除）、SHA-256、原始review/独立脚本与输出、复现命令和环境；包含被测实物，不要求记录文字自指最终hash。生产matched body=false、LVS not_run；产品parser/runtime/Stage1–6、publication、完整grid/CSP/DTO/codec/CAS、真实PDK/Calibre、production downstream tool gate、Virtuoso/SKILL dry-run和旧readback未消歧范围均未运行。KLayout expected几何序列化独立，unit encoder共用已披露；不把synthetic通过作为生产通过。

**交回PM。** 以同一新版身份核对R1–R5/V1–V7及原22目的、独立review处置，再闭合受影响MR/人工结论；保留既有确认，不重复要求已定选择。尚需PM处理MR-074-Q1及其未消歧scope、MR-051经052收窄后的样张结论、相关A/B/C/D新版人工闭合和真实生产准入缺项。执行者不最终验收W004、不关闭W003、不进入M1 parser。

### E4. 原路径提交与 GitHub 交付（2026-10-31）

E3/R2及封包身份记录的是提交前的受测/受审版本；其“未授权提交/推送”“仅本机路径”是当时事实。本轮用户随后明确要求“对照repo内原来相应fixture等所在位置，将你的更新以git push可更新的那种形式，推送到github上”，据此授权本次提交并推送到现有`codex/w004-task-convergence`分支，不合并main、不删除分支、不改变PM验收状态。

本轮恢复核对本地HEAD与远端分支均为`9f6735dcede8e8b2135f89ff10f079a752ed758b`，staged为空；原149个修改/新增/移除路径逐一与交付包identity一致。fixture、support、合同、报告、图和review原文仍在原路径；仅追加本段和W003附件导航。没有重新运行修订、生成器或产品/EDA验证；之前验证与review的适用范围继续按E3/R2及原包说明。

为解决PM实例不能访问本机工作目录的问题，将原`artifacts`目录的9个文件逐字节转存至[W004交付附件](W003/delivery/w004-20261031/)，包括[原始完整封包](W003/delivery/w004-20261031/W004-delivery.tar.gz)、[封包独立审计](W003/delivery/w004-20261031/W004-package-audit.md)、[原校验清单](W003/delivery/w004-20261031/SHA256SUMS.json)、原binary patch、原图及校验回执。该目录是受审交付的不可变历史附件，当前可编辑fixture仍由原路径拥有；包内的本机路径用于说明历史执行位置。

原包大小为10,570,253 bytes，SHA-256保持`3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39`。本轮只做原身份比对、转存字节/清单核对、文档链接及Git差异检查；发布commit与远端核验结果由Git和交接回复标识，不追求文档自指hash。原包和工作区恢复证据保留。MR-074-Q1等人工闭合、W004最终验收、W003关闭仍归PM，未进入M1 parser。

## Review 结论（reviewer）

当前收敛review只检查原决定覆盖、范围/依赖、候选状态、验收可执行性及是否越界。尚未开展新版样本review；未来由未参与修订实现者绑定完整版本，核对独立答案和实际证据。准备review或旧W003技术通过都不自动覆盖新版样本。

### RP1. 独立执行准备review（2026-10-31）

Reviewer：`w004_preparation_review`，未参与本轮准备正文编写。结论：**0项必须修正findings，可交PM接收执行准备；不构成样本实施许可或W004最终验收。**

受审基线为`work@da55ca656e5e38caba1e7f47483137c68c044907`；review-input完整snapshot/patch位于`/workspace/w004-preparation-20261031/review-input/`。Reviewer独立核对工作区与snapshot一致：W004 SHA-256为`57d03ade619cb9ceb8acfa09053e22a40e48700bc0efc4c3661baa38c3c3de8a`，current-work SHA-256为`5b6f7b46c37351cf05fe8c93753e70688b74b30b8f75d2ac0f823aacab4c17dd`。这些身份覆盖追加本段前的两份文档，不自指追加后的文件。

| 核查项 | 独立准备review结果 |
| --- | --- |
| 要求与依赖 | 回查MR-002/004/020/030.2/034/040/046/051–052/074/076及相关架构原文，R1–R5有效要求有对应交付/证据；已定方向、措辞建议、待决表达和后续产品实现区分清楚。实际F/H/D路径及共享集成次序可定位，未引入完整grid/CSP/DTO/codec/CAS门槛 |
| 三项待决 | D1说明外部body输入、scope、来源闭包、本地graph与context association差别，保留C22缺必需支持目的并区分几何失败；D2是推荐后置而非宣告MR-040已获批准；D3先明确scope再统一ID，不把dry-run等同apply或独立GDS回读 |
| 后续验收 | 与实际cases.json逐项核对22个原case身份/目的和P/S/E分组；独立答案、raw-normalized、实际overlay应用、closure/hash/refs、正常及8失败人机报告和原F1/F2均有后续方法。已读取相关helper源码确认覆盖限制，未把helper断言扩大为产品运行证据 |
| 范围与停止点 | 核查仅W004/current-work两文件改动，staged/untracked为空，旧W003 E/R及MR、fixture/helper/附件/架构/产品/legacy无diff；明确交回PM后停止，未从旧prompt或历史发布授权推导继续实施/提交推送授权 |

独立专项代理`body_scope_review`未参与原编写，另对D1/D3回查MR-046、P7、架构§3.6/4.8/12.5及§10.3/10.5，并对照tech/spec/oracle/C22/check IDs，未发现必须修正问题；其结论只涉及候选表达和边界，未验证候选几何或新版schema/运行。

主执行准备代理的文档初检证据为`review-input/checks.json`：25个相对链接/锚点、11张表、22个迁移目的及diff格式通过；主代理另报告从HEAD两份原文应用完整patch可逐字节重建受审snapshot。Reviewer核验了snapshot身份、实际修改范围及22个case对应，不将上述主代理检查冒充本人的重复执行。追加本段后由主代理另做最终文档检查与snapshot/manifest。

限制与交回：本次只做准备文档及静态来源对照，未运行生成器、fixture校验器、pytest、产品或EDA，也未复验旧Mac附件。D1–D3仍待PM及必要用户语义决定；新版实际输入、几何、反例、报告和产品行为均未由本review验证。下一角色仅为PM接收准备结果并明确后续范围，执行者不得自动开始样本修订。

### R2. 新版独立review及修复复核（2026-10-31，reviewer原文）

Reviewer：`independent_review`，未参与实现。对冻结 `review-r3/snapshot` 的145文件逐bytes核对，manifest SHA-256为 `9136e0509ab50e03ea260eb0d1ecaedfb4aa6a58cda17a5cc926d715de0fbd76`。原IR1–IR5及r2残余均修正并独立复核，剩余必须修正项为0，可交PM接收实施交付。独立stream/CDL/Fraction计算得到40本地图形、8边、6本地组件、两条外部context支持关联；29个实际overlay保留C01–C22及7个body见证。raw/F1/F2独立专项、133处文件/JSON pointer引用、D3八行义务及116文件/图/记录再生成实物对账通过。原finding和修复证据保留，完整结论见新增review附件。此结论只覆盖synthetic样本及辅助材料；production matched body=false、LVS及真实工具未运行，不构成W004最终验收、W003关闭或MR-074-Q1等人工结论关闭。最终review附件/patch封包另作身份核对，不能冒充该快照已包含后续新增正文。


原文与处置保留：[初审IR1–IR5](W003/reviews/independent-r1.md)、[第二轮残余](W003/reviews/independent-r2.md)、[第三轮最终复核](W003/reviews/independent-r3.md)、[raw专项初审](W003/reviews/raw-r1.md)及[修复复核](W003/reviews/raw-r2.md)、[owner专项第三轮](W003/reviews/owner-raw-r3.md)。这些附件是reviewer所写原文的逐字节副本；独立脚本、实际overlay、命令/环境与stdout/stderr随完整交付包保存。最终复核报告SHA-256为`56c89de6087c92f3ba215a7f8fa4ed5c035e51b07f3939476f2b3daedad86822`。

最终附件加入后，执行者重新生成相对准备提交的完整binary patch并在独立基线目录实际应用，核对全部新增/修改/移除文件。被审fixture/helper/报告/图与145文件r3清单保持同一bytes；仅W004身份/交回文字及新增review原文在其后加入。最终完整snapshot/patch和SHA-256由交付包identity.json/SHA256SUMS.json标识，避免自指hash。最终Git状态为未提交工作区交回，未推送/合并/删分支。

## PM 验收与交接（PM）

已建立任务并按最新指令收窄下一session范围，**任务收敛本身仍待下一session完成**。收敛结果接收后，再明确启动实际修订；最终必要修订、独立review及人工结论闭合后，PM一次接收W004并在W003补闭合依据，随后才派发M1 parser/输入绑定。

2026-10-31准备时`git fetch/ls-remote`成功：审核分支为上述b41ba92，main为b1f0301cf76b2e1808cb293cfdb4e1bfededde73，main是审核分支祖先，审核分支领先4个提交。用户本轮明确授权提交推送这些PM文档；具体推送结果/最终SHA以交接回复和远端核验为准，不作自指提交hash。未授权执行本轮main合并或删除审核分支。

跨session使用本轮已发布分支+SHA+任务路径；不要只检出旧b41ba92后重建旧版W004。共享环境配置不保证共享当前实例磁盘；接手须确认本文件含“仅任务收敛”。若缺失，先取得本轮发布版本，保留本地已有修改，不覆盖另一session工作。不依赖旧Mac临时包。

前一版任务文档曾经`handoff_prompt_review`复核，SHA-256为`58b59545f5242e6467bfcff4027688c556b2dd5c9b244e5277f5858d29e0a14a`；其“可开始实际修改”安排已由本轮用户指令替代，旧身份不作为当前版本的review证明。

本轮“仅任务收敛”任务文档及五份入口经`w004_convergence_check`独立只读复核，无必须修正问题；受审W004 SHA-256为`89994271fa2894e38388dc84ce89434166362c47312a0f2aa4f68438d5b615ba`，之后仅追加本段复核事实。79个相对链接、diff格式及原W003执行/reviewer正文保留检查通过。此结论只覆盖交接文档，不表示任务收敛已完成或新版样本通过。

### 下一session prompt

```text
按Layauto项目规范，完成W004的任务收敛/执行准备；本session不修改样本。
从交接指定的codex/w003-manual-review已发布提交恢复，先核对branch/HEAD和已有差异。
读AGENTS、README、协作规则、current-work、W004及MR-076，按R1–R5回查原MR、架构与实物。
只读调查后，在W004形成：精简要求表、文件/依赖表、最少待决项及推荐、后续验收清单、实施顺序和停止点。
区分已定、候选和后续实现；tapcell方向不用重问，具体body输入与MR-040配置精简未批准。
只写任务准备文档及必要恢复入口，不改fixture/helper/既有合同报告、架构或产品，不运行改写产物的生成器。
安排独立准备review，检查覆盖与边界；交回PM接收后结束，不自动进入实际修订。
保留原W003 E/R及人工决定。提交/推送按该session明确授权，不能把本轮发布授权泛化为以后合并/删分支。
```
