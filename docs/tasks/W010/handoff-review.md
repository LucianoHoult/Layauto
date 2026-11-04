# W010 派发要求独立复核

日期：2026-11-04。Reviewer：`/root/w010_handoff_review`，未参与本轮范围调查、任务起草、产品方案或实现。上游接口只读专项：`/root/w010_handoff_review/upstream_scope_check`。

仓库 `/workspace/Layauto`，分支 `codex/w010-local-contact-connectivity`，基线 HEAD `3be0b98359038bab6c23980b55a48987cc71a369`。该基线已包含 W009 PR #63 的 main 集成及最终验收补记。本轮只复核尚未提交的 `docs/tasks/W010-local-contact-connectivity.md`；开始时该任务为唯一未跟踪文件，随后观察到 PM 正在维护导航文件，均不作为本 reviewer 写入。

**初审结论：必须修正项0，范围在现行 synthetic/toy 合同内可执行；两项非阻塞澄清建议由 PM 采纳。** 本复核是派发要求审查，不代表未来实现方案、代码 review、产品验证或 W010 PM 验收。

## 受审身份与建议

初审任务全文 SHA-256：`b14f7051591a8ace8b888e62248afbaa29bc6f8f61dedff093b351c0c01ec4fa`。该文件未进入基线 Git 对象，不能只用 HEAD 代表受审内容；PM 后续提交会随该任务保留实际文本。

| 项目 | 初审判断与建议 | PM处置 / 复核 |
| --- | --- | --- |
| 已消费 rules 的来源绑定 | 任务行为1/6及A1已要求同一捕获owner认证，技术上可实现。建议明确新增rules payload与实际tech/rules捕获及其source role关联，避免只仿照W009 physical绑定而遗漏新消费的rules provenance。非阻塞澄清。 | 已采纳。行为1明确payload等于同捕获tech/rules，SourceRef绑定实际rules source role，不靠同名文件/另配副本；最终复读通过。 |
| 重复 connector 与重复导体 region | 独立有效region按来源record计数，connector端点歧义不能先component合并，要求正确。建议明确重复connector record须各自保留provenance/逐侧audit，拓扑可相同；A4的“重复record拒绝”指造成多端点的独立导体region，避免误读为重复connector也一律拒绝或去重丢失。非阻塞澄清。 | 已采纳。行为3保留每条connector来源/重数/逐侧audit，允许相同端点拓扑聚合但不能丢证据；A4明确多端点来自独立导体record，重复connector自身不一律拒绝；最终复读通过。 |

## 对照依据与技术判断

读取根 AGENTS/README、协作规则、任务完整要求及执行prompt，核对所引架构的 Stage2、坐标/occupancy/physical connectivity、FIN/gate/OD/CUT、规则relation与domain/state边界，W003现行合同、manual MR-045/047/052/054/056及W004现行body修订；实际读取 `tech/physical.json`、`drawn.json`、`rules.json`、`coordinate.json`、正常/special oracle与spec、via_enclosure样本语义，并检查W008/W009输入、有效区域及codec的实际保留链。

1. **依赖与来源足够。** W009成功结果保留完整W008/GeometryInput/NormalizationInput捕获链；`tech`仍有physical/drawn/rules/formats及各owner源引用。W008已对这些捕获重建认证，W010可在纯normalization适配中取同源rule，不需要新文件格式或重新读盘。中立state/domain不反向依赖parser，符合架构所有权。
2. **图节点及正常答案一致。** W009提供4个OD空间端区、3个LI有效region；原图形提供1个POLY、4个M1和BODY_N/P各1，共14节点。现行独立oracle为8条connector边、6个完整分量，两个本地BODY各独立。channel仅隔离OD，不作导体；POLY保持连续；FIN/CUT/FRAME/MARKER不被误作导通节点。任务没有按net标签生成组件或把S/D器件关系当导体边。
3. **接触及端点单位准确。** `same_layer_contact/1`明确正面积或正长度共享边成立，点/角触不成立。`cross_layer_contact/1`和局部三类drawn声明均按每侧独立effective region正面积计数，不能用same-layer component合并消除多端点或先用enclosure挑选端点。W003现有独立fixture verifier对effective region逐项求端点后才union，与此相符；该helper仅作已声明样本语义的交叉核查，不作为未来产品runtime依赖。
4. **物理导通与规则判据分离正确。** 当前T05明确局部CONTACT/VIA0/GCONTACT与外部BTAP分域，required geometry-only两侧包围至少1nm。`via_enclosure`中的VN仍与LN/MN各唯一正面积交叠，因此edge必须保留、LN侧包围违例必须显式表达。任务要求exact集合包含、允许边界等号，并按精确单位换算，能覆盖孔洞、多矩形分解和非整数tick阈值，避免bbox/单片/浮点替代真值。
5. **完整坐标与索引未被虚构。** coordinate owner明确example-only且不是完整runtime模型。exact局部接触可先交付；W008 raw axes只作候选索引，任务要求候选覆盖共享边和切后多片并允许诚实的有限精确扫描。未将内部差集分解、32×16示例或FIN pitch升级为制造/routing lattice；完整坐标及有效region投影仍保留后续义务。
6. **公开边界和错误覆盖明确。** 行为6/A6要求完整节点/边/分组/audit重建、closed/versioned wire、递归不可变及对遗漏/多边/外来引用/假audit的拒绝；不仅检查私有helper。新图算法和整个W009/base/捕获/readback链均须保持意外异常对象及既有cause/context/suppression，畸形wire另作明确拒绝，已吸收IPMR-01/FXR-01的经验而未放宽标准。
7. **body与后续范围准确。** 本地BODY仅保留几何节点/同层事实；外部6图形与body-to-rail关联不进入本地图，非空本地BTAP不被顺手接纳为新能力。U06生产leaf cell缺上下文、完整body/FIN/器件提取、标注、其他mandatory/lifecycle、事务与lineage、baseline/no_change/Stage6均后置且不冒称通过，当前无需追加grid或tapcell用户决策。
8. **可观察验收具备独立判据。** A1–A8结合真实捕获链、手算正常成员、special三分量/零边、规则违例仍保留edge、独立数学/歧义/公开constructor及nested wire反例、双解释器/typing/包/安装与最终身份，不只比较数量或同算法自证。复杂度和有限压力规模须如实披露，没有增加无依据的外部输入上限。

## 方法与限制

本轮只做静态规范、实际owner/样本、上游代码及任务文本检查，并计算任务全文SHA-256；未运行产品测试、构建、安装、性能或EDA检查。W010尚无产品实现，方案/代码及其工程结果仍需后续各自独立review与PM核验。

唯一写入为本报告；未改任务、导航、产品、正式测试、fixture、答案或历史证据，未提交/推送或启动执行。

## 最终文本复核

澄清后任务全文 SHA-256：`215bd28756437a019fe7ba6a5471bb7c23f238cb0d4e1173197ed1333879718e`。Reviewer已复读行为1、行为3及A4的实际修改，两项建议按现有合同落实，没有新增输入解释或扩大能力。

PM补充阶段/接收说明后的最终任务全文 SHA-256：`91ff46639a9816b9f3856670c6b8daec264cab91bfe59d083a45778778967e1c`。Reviewer再次读取最终阶段及PM段，在内存恢复两处阶段/PM文字后重算全文SHA，精确得到澄清稿`215bd287…`；再逆替换行为1/行为3/A4三处澄清，精确得到初审`b14f7051…`。这核实最终稿相对初审只有已读的两项澄清及派发阶段/PM事实补记，行为要求和A1–A8没有未审变动。检查没有改写任务文件。

**最终判断：必须修正项0，派发范围可执行，最终“可执行”阶段与本次复核相符。** 方案/代码/工程验证仍未执行；此判断不代表产品方案、代码、完整ConnectivityState或M1/生产准入已通过。若后续再改变行为/验收，须检查受影响结论。
