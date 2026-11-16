# W014 独立代码 review

Reviewer `/root/plan_review` 未参与实现或正式测试编写；此前只承担独立方案
review。规则专项 `/root/plan_review/rule_scope_check` 只读核查外部 body 实现。
**结论：W014 授权范围的独立代码 review 通过，未关闭必须项0，交PM验收。**
最终工程原证据已由未参与实现者独立核验；本结论不代PM验收或生产准入。
下文finding保留发现、修正、复核及调查纠正的原时点记录；其中历史“待验证”
描述以本节及“最终工程证据”节为最终状态，不改写原失败。

## 最终被审身份与要求核对

已审冻结提交`66f5b1e5369549ed8df361f89f099acfd2f39e17`，source_id
`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`，
286 selected/111 runtime；独立Git archive/live/manifest逐字节核验见
[冻结审计](review-evidence/resource_freeze_audit.stdout.json)。最终受测集合为1889项，
typing目标65源。CR01–07、CR09–12已复核关闭，CR08的public漏洞归因已撤回，
工具EG01已修并由实际双安装smoke验证；原finding、失败输出、调查纠正均保留。
最终A1–A9在本任务有限范围内闭合，没有未关闭产品must。

| 要求 | 独立核查与有限结论 |
| --- | --- |
| A1 同源组合 | 实读公开W010完整重认证、neutral owner/source闭合与W011/W013两侧接口。两body sources有序绑定context owner与实际GDS；source/seed/derived/local/body均闭合capture集合，query run/database及tech/geometry owner由共同中立链核验。原source/ref/旧wire未改 |
| A2 本地六端 | D/S取现行ordered topology，G保留共享物理component而target仍逐device；observed仅取W013证据，expected另存source CDL。unknown/conflict/mismatch不通过交换S/D或抄声明消除；端口名称不证明pin access |
| A3 外部body | 实核GDS/top/FRAME/对象/单位/profile绑定与BTAP全部消费字段，精确正长度FRAME续接、正面积tap接触、唯一候选及exact rail query锚；外部关系独立，本地BN/BP仍unknown且无物理union |
| A4 body规则 | 全local/external域异型body pair与全部external taps均审计，active enclosure、tap body/rail enclosure取同源rules；保留本地T05。几何chain、rule、claim分别报告，exact锚后传播真实rail component冲突，不把有限body检查升级为全部mandatory |
| A5 错误/精确 | 核既有body见证及reader/W009实际拒绝阶段，原证据与定位保留；独立800组Fraction边/面积/margin核查及45.05对45反例。无context/operator、错类型/绑定、歧义/断开/违例不是可任意降级的unknown；未终结run |
| A6 完整性 | 每个准入source device保留D/G/S/B，missing channel仍有四个target及缺项；W011原FIN4对source5差异、W013coverage/conflict及其issues保留。八端一致不升级成完整参数/model/VT/LVS/no_change通过 |
| A7 DTO/资源 | 实核原native/storage防alias、class-default兼容、所有SourceRef/EvidenceRecord外壳重构、Result与neutral全部实际保留字段比较、封闭wire及原异常历史。只有一个完整W010 captured输入，不套两份完整Result；三路R4成本与旧reference采信独立598项通过，精确clearance只放行工程调度 |
| A8 U06方案 | 已独立审production-body-scope四类输入→输出/允许与阻止操作，区分本地已知、父级未知与未证明body路径，明确可信替代/人工意图的证明边界；仅设计，现reader的body_context必填未改 |
| A9 工程/review | 方案门先于runtime；开发165范围按独立核对的85前缀采信+80实际通过闭合。最终新冻结源双3.10/3.12各1889 passed、typing各65、build、双clean安装源码外三路smoke全部实际通过，独立840项工程审计闭合21条原命令/原logs/身份/时间与包字节 |

## 最终工程证据

独立专项`/root/plan_review/final_evidence_review`未参与产品、正式测试或工程runner
实现，实际执行只读[final_engineering_audit.py](review-evidence/final_engineering_audit.py)，
**840项通过**，见[原审计结果](review-evidence/final_engineering_audit.stdout.json)及
[专项记录](review-evidence/final-engineering-notes.md)。主reviewer另读实际最终
receipt、双pytest/typing原输出及双安装smoke输出，核无受测source/test/config差异。

| 实际解释器 | 完整pytest | strict typing | clean安装与源码外smoke |
| --- | --- | --- | --- |
| Python3.10.22 | 1889 passed，10784.59秒 | 65源通过，pip check通过 | 从本次sdist安装，三路smoke exit0，461.918秒 |
| Python3.12.14 | 1889 passed，7731.42秒 | 65源通过，pip check通过 | 从本次wheel安装，三路smoke exit0，328.685秒 |

双collection均保留原1731 IDs，新增158，无原项缺失。build实际通过；wheel、
sdist和双clean安装各111 runtime文件与冻结源逐hash相同，实际pip安装artifact
SHA闭合。双安装均从checkout与snapshot外cwd以`-I -B`调用实际site-packages，
三路normal direct/readback/extraction mismatch均有8端、6本地+2独立body、
14/8/6本地图及BN/BP unknown、公开roundtrip/digest、FIN4对source5保留与
unsealed/attempt/checkpoint不变/无terminal的原输出。

完整286 selected文件的Git commit、live、原tar及manifest相同；21条实际命令
的exit0、stdout/stderr hash、解释器/依赖、真实UTC时间、matrix→build→串行
安装smoke顺序闭合。冻结runner/source_identity/smoke和原clearance均未改。
[最终原receipt](verification/receipt.json) SHA-256为
`fbfd34d4c63e00c6e1cdd5a340487be6306a10bb0707605a229b4eaa527fe938`。
此审计只读取既有证据与包，没有重复执行pytest、build、安装或捕获/codec。

审计脚本兼容3.10旧pip的显式`archive_info.hash`和3.12的`hashes.sha256`；双字段
存在时必须一致。原审计脚本快照、真实pip报告读取和矛盾控制证据保留，未改
工程runner或掩盖工程失败。

## 初始审查范围

从方案提交 `40559e0186f7d80bb8a7f3256c900e0fadd66191` 的工作区开始，
核新 domain/derive aggregate/normalization/codec、正式 W014 tests 及 task 执行段。
最初 `derive/body_relations.py` 尚在实施，不将未完成文件记作已审或缺失功能 finding。
未改被审 runtime/tests/fixture/PM 段；独立探针仅写本目录 review-evidence。

## Findings

### CR-01：新 DTO 保留旧叶的未声明可写存储（必须，已关闭）

原 `domain/terminal_relations.py:validate_terminal_graph` 只对来自新 terminal/derive
模块的 dataclass 核 `vars` 字段全集，旧嵌套 typed leaves 和 FrozenMap 未核
未声明存储。构造正常 TerminalRelation 后，给其 `expected.source`、`expected`、
DeviceId/CellId/NetId 或 LocalRef 注入 `undeclared_extra=[]`，新 relation 的公开
`replace` 和 `to_value` 均接受，保留该可写 alias；修改 alias 时 canonical wire
完全不变。exact FrozenMap 加同类属性也被新 validator 接受。违反 A7 的 no-alias/
closed retained storage，且序列化悄悄丢弃实际保留的字段。

独立复现：[leaf_storage_probe.py](review-evidence/leaf_storage_probe.py)，
原输出 [before](review-evidence/leaf_storage_probe.before.stdout.json)。
初始六种旧叶全部 `rejected=false / retains_alias=true / wire_ignores_alias_mutation=true`。
另独立短 probe 确认 FrozenMap extra 也接受；正式修正需包含 map 分支。

关闭条件：在 W014 新边界检查全部保留 dataclass/Exact FrozenMap 的声明字段全集，
在防御复制前拒绝额外可写存储；保持旧类型/旧 codec 原合同字节不变。新增正式
回归，并由 reviewer 对源身份和独立 probe 复核。不能只删现有 module 限制后
漏掉先分支处理的 FrozenMap，也不能通过复制掉 extra 来掩盖原输入不闭合。

执行者已在新 validator 对所有保留 dataclass 核声明字段全集，在 FrozenMap
专门分支核唯一 `_entries`，并将新公开 `_require_input` 改用该 validator，未改
旧 DTO/codec。本 reviewer 实际复跑原六叶探针，全部 `rejected=true`；见
[after](review-evidence/leaf_storage_probe.after.stdout.json)。另独立
[map_storage_probe.py](review-evidence/map_storage_probe.py) 检 extra/list backing/
重复keys/缺backing/循环五种 exact map shell，全部拒绝，见
[输出](review-evidence/map_storage_probe.stdout.json)。复核时 domain 文件
SHA-256=`94255da6a518fe305d713634daf4ce1cce1791361f79084da928981d039654d0`，
normalization 文件=`456f5421607812a6a65bc36d6d87b64c95322d2d52def37da4804a0a9acce27e`。
据此关闭，不把初始接受改写为已通过。

后续真实readback早期资源检查发现上述严格vars全集实现误拒合法旧DTO：
publication.RunRequest/RunAttempt等的kind是`field(default=...,init=False)`，
正常只存于class。原失败保留于resources-early/w014-normal-readback原日志。
reviewer另用 [readback_default_storage_probe.py](review-evidence/readback_default_storage_probe.py)
独立构造两个合法旧DTO（无capture），二者均被误拒；
[before](review-evidence/readback_default_storage_probe.before.stdout.json)绑定domain
SHA `20f1b840091a77b04e39abce82ce2901af5bc68468b6c947cb6cfba2a9219779`。
因此重开该finding的兼容残留：须允许合法不可变的class-held init=False默认，
继续拒绝extra/missing required fields/alias，旧DTO/codec不变；待修后复跑。

兼容修正后，新guard只允许可由静态dataclass默认明确解析的有效字段，必需及
default-factory字段仍要求实例存储，extra仍拒绝。reviewer实跑
[default after](review-evidence/readback_default_storage_probe.after.stdout.json)：
两个合法旧DTO均接受，domain SHA=`d7654ce54ab139f4be690d5616393cc503cd2bf1b660930273fece4bc8b09b89`；
同时原六叶alias与五map恶壳再次全部拒绝（各after-r2输出）。此兼容残留关闭，
真实readback的完整成功仍需最终资源/工程证据确认，不以小DTO probe冒充完整链。

### CR-02：coverage 将允许的未知 LVS 状态改写为 not_run（必须，已关闭）

`derive/terminal_relations.py:coverage` 初始硬编码 `lvs_status='not_run'`，而
reader `_body` 明确准入 `('not_run','unknown')`。仅将临时 context.lvs_status
改为 unknown 并重绑即可准入；新 summary 不应将未知事实重写为 not_run。
完整输入虽保留原值，也不能让公开 coverage 给出矛盾事实。

关闭条件：coverage/body compact输出保留实际已认证 status，补准入unknown
临时变体；normal fixture 的 not_run 不变。此项来自真实分支静审，尚未执行
完整捕获探针，待实现就绪后按共享 neutral local 核验。

执行者已从 body_evidence.payload 保留真实 lvs_status，body compact同样保留。
本 reviewer 实际运行 [body_scope_probe.py](review-evidence/body_scope_probe.py)：
一次临时真实 local/shared neutral 输入，normal与真实reader准入的unknown变体
分别得到not_run/unknown，coverage/body两列一致；见
[原输出](review-evidence/body_scope_probe.first.stdout.txt)。据此关闭。

### CR-03：raw body URI 可以选择已占用的错误 captured role（必须，已关闭）

初始 body evaluator 只比 source_gds.sha256/top；聚合 _require 将 raw URI
解释委给 evaluator，后者未核 URI。新 neutral 构造若把 URI 改为已存在的
source.cdl 而保留 GDS hash，会忽略明确的 role 矛盾。必须保持旧认证语义：
已在source表中的URI必须指向实际GDS角色；未出现的历史alias不能因本轮而
被无依据禁用。此缺口由静读旧 geometry_input.selected 与新 body 分支发现；
修前代码仍在执行的first-normal源码快照中，本次没有冒称运行过修前此变体。

执行者已补对应captured-role检查。reviewer的body_scope_probe实际运行
source_gds.uri=source.cdl的neutral变体，产生located BodySourceBindingMismatch，
两个context chain失效、observed清空，未冒称拒绝到reader或raise；结果是保留
事实的diagnostic draft。按该结构拒绝能力复核关闭；其rule_status矛盾另见CR-05。

### CR-04：前一器件局部 body 错误污染后一器件（必须，已关闭）

body evaluator 每device末尾以 `issues[:start]` 搜全局绑定失败；这也包含此前
device的局部BodyObjectBindingMismatch。真实reader临时变体仅改
MN0.association.local_body=BP（两者role都是body，reader准入），MN0产生局部
错误后continue，MP0自身全链正常却被前一错误清空。body_scope_probe已实际
确认MP0 chain=indeterminate、observed=[]。须把真正全局失败与各device依赖
scope分开；修后MP0仍建立VDD关系，MN0继续报告原局部错误。

修正将global_binding_invalid冻结在device循环前。reviewer实跑
[body_scope after](review-evidence/body_scope_probe.after.stdout.txt)，MN0局部错误
仍定位，MP0恢复established/VDD、rule satisfied；关闭。

### CR-05：绑定失效后仍报告 body rule satisfied（必须，已关闭）

path先计算rule_status，之后全局绑定失效只改chain/observed。实际neutral
wrong_top以及wrong captured URI的probe均得到chain=indeterminate、observed=[]，
却rule_status=satisfied。须保留原几何margin/接触事实，同时使依赖失效绑定的
T04/path规则状态不再宣称满足。原输出与CR-04共用同一body_scope_probe证据。

修正先将global有效性纳入geometric，再派生rule/claim状态。上述after实跑中
wrong_top和known-wrong URI均为chain/rule indeterminate且无observed，原物理
数值仍保留；关闭。

### CR-06：任意坐标接续被误作 FRAME 左边界接续（必须，已关闭）

generic edge_length与external.x_max<=frame.x_min不足以证明接续位于FRAME。
反例把MN local BODY_N/M1左边改-10，context local bindings同步，external
body/rail右边改-10，tap移至[-18,-14]并保持相同Y；VSS rail query精确同步到
local新矩形。active和tap enclosure仍满足，generic接续长90/10，但接续x=-10
不等frame左0。W008/W010尚未执行T01，不能假定local containment已成立。
方案及已消费operator要求frame boundary；需显式两侧接续边坐标等于FRAME左。
独立专项已运行纯边/包围反例；完整captured反例另行归档，不以纯helper测量
冒充端到端结果。

随后 reviewer 已真实执行临时GDS/raw query/context重绑的完整neutral组合：
移至-10的接续仍得到issues=[]、B equal、chain established、rule satisfied。
原 [before-r2输出](review-evidence/body_conflict_frame_probe.before-r2.stdout.txt)
与 [探针](review-evidence/body_conflict_frame_probe.py) 绑定保存的
[修前evaluator](review-evidence/body_before_scope_fixes.py)，SHA-256
`02861e79c2f7a2563c62ebc96e3c04e63f0ed6453bcc6ab5451dac76aebe1df5`。

修正增加frame_edge_length并用于全部候选，要求local.x_min==external.x_max==
FRAME.x_min且Y交集正长。reviewer对同一真实GDS/query/context变体实跑
[after](review-evidence/body_conflict_frame_probe.after.stdout.txt)：报告
BodyContinuationMismatch，MN0.B indeterminate，独立MP0.B仍equal；数值边长
90/10继续另列。关闭，没有以少跑T01或未知事实掩盖此scope要求。

### CR-07：完整 rail 证据遮盖同一分量的部分冲突证据（必须，已关闭）

body仅取完整exact rail seed的NetId，忽略同rail其他正面积query冲突。保持正常
VSS完整rail，加VDD部分矩形(0,48,20,58)，W013会报告同rail/component冲突，
但B可能仍observed={VSS}/equal、path.rule_status=satisfied。不能让全尺寸seed
获得未声明的优先级。须在存在exact锚后传播真实rail分量的冲突net/evidence，
使B行conflict/不确定；没有exact锚时仍unknown，不能靠component已知跳过精确
证明。root已确认此为A2/A6内must，完整独立反例待归档与修正复核。

同一次body_conflict_frame_probe已实际确认：W013两项冲突issues存在，但MN0.B
仍equal/VSS，path satisfied；见上面before-r2原输出。此探针只用真实reader
构建所需输入及neutral local，不构造完整Result/wire。首次脚本因动态import未
设包名而失败，原stdout/stderr保留；修复review脚本后才有上述实际结果。

修正只在exact rail anchor存在后合并该真实rail component全部net/evidence；
缺exact仍不能凭component建立body证明。reviewer同一after实际得到MN0.B
conflict、observed={VDD,VSS}、rule indeterminate，MP0不受影响；关闭。

### CR-08：gate_operator 调查（原必须项归因已撤回，上游已有防护）

W014用连续POLY/shared gate关系比较G端，但 _EXTRACTION未核
device_extraction_contract.gate_operator；schema将其作为text，旧W010/W011
也未执行它。仅改成“POLY is severed at each recognized channel”，不能仍静默
使用旧连续解释。须在新消费者核现行完整文本与located unsupported反例，
不改旧合同或自行支持新物理语义。此项静态确证，尚未跑完整输入变体。

执行者已将现行完整gate_operator加入_EX​TRACTION，并新增真实public入口
正式变体。本reviewer实际运行 [owner_exception_probe.py](review-evidence/owner_exception_probe.py)，
用真实三份owner JSON构造小中立owner：gate、BTAP连接、BTAP predicate、rule
evaluator四项改变均被located unsupported拒绝；gate精确定位
`/device_extraction_contract/gate_operator`。阈值10/1与改为11/1均直接来自native
int转Fraction。另六项已处理schema错误之后的RuntimeError/KeyboardInterrupt/
SystemExit×suppression False/True原异常identity/cause/context/suppression全保持，
见 [原输出](review-evidence/owner_exception_probe.stdout.json)。body修后SHA为
`be59c340a021d9a9a3f25fa97729a8f2040c769522c9d36cbda6595377cad485`。
此实跑是owner边界与异常历史，不冒称已运行新public全捕获变体；关闭该实现缺口，
正式变体和完整工程证据仍待最终身份核验。

**后续实际纠正：** targeted-r3在上述正式public变体失败（64 passed/1 failed），
原因是W009已在`domain/regions.py:CONSUMED_PHYSICAL`和OperatorBinding构造
核`/device_extraction_contract/gate_operator`，返回UnsupportedRegionOperator；
测试helper build_local因此在到达W014前断言失败。原stdout、命令、完整source
identity/snapshot保存于development/targeted-r3*。我先前只核W010/W011，漏看
W009，是review调查错误，不能据此声称新公开链曾接受该改变。

原finding及owner小probe保留，**撤回“public链缺gate防护”的must归因**；W014
新增中立防御可以保留，但不宣称它修复了原公开路径。正式回归改为真实
reader→W008→W009的实际拒绝，并确认W014未调用；待修后targeted/最终矩阵
核验。该纠正只改测试阶段假设，不改runtime或资源workload。

### CR-09：foreign leaf root 先构造旧注册类型而泄漏 TypeError（必须，已关闭）

新codec kind=record分支先`_unpack`，之后才核根是否是三个新叶。用合法
RunRequest经其注册表pack后放到该根，_unpack把init=False的kind当constructor
参数，泄漏TypeError而非closed foreign-root ValueError。
[独立probe](review-evidence/foreign_root_probe.py)与
[before](review-evidence/foreign_root_probe.before.stdout.json)已实际复现。
应在leaf根分派前限制TerminalRef/TerminalTarget/TerminalRelation，不以catch
任意TypeError补洞；保留合法子叶的原异常历史，新增此foreign root回归。

执行者把通用注册表缩小到3个新叶及实际必要的9种旧叶；leaf envelope先拒绝
foreign root，再进入unpack，nested foreign也不在注册表内。reviewer按相同旧
RunRequest字段形状构造包，实际得到ValueError(foreign terminal root wire record)，
见 [after](review-evidence/foreign_root_probe.after.stdout.json)；未捕获任意TypeError。
原before中由旧codec._pack构造包，修后probe改用明确旧字段构造同类形状，
避免新的_pack先拒绝遮蔽decode入口。关闭。

### CR-10：Result 静默丢弃被改的 Draft 保留输入（必须，已关闭）

_validate_result只比较compact输出；value的local/source/seeds/owners/capture等
保留输入不在投影中。root自审提出source.dialect反例后，reviewer独立执行
[retained_draft_inputs_probe](review-evidence/retained_draft_inputs_probe.py)：真实
normal捕获构建Result，仅unchecked更改value.source.dialect='forged'且保留原
全部输出，encode实际接受并生成23450036B包，静默使用正确重建值丢掉caller
被改存储。codec SHA a64f2d42…，原输出
[before](review-evidence/retained_draft_inputs_probe.before.stdout.txt)。

须在Result公开encode验证所有实际保留字段（root完整input仍走现行公开认证，
不重复嵌套/序列化大包），不能只比摘要或把伪造字段复制掉。原存储先native/
closed检查，再与完整重建对象做canonical字段比较；不靠私有“已认证”标记。
正常encode成本变化需新的W014三路资源实测，原W013reference可按依赖身份采信。

执行者新增_stored_value/_retained：已校验的原存储按typed class/字段/map/tuple/
scalar区分后做完整canonical比较；Result只跳已完整公开认证的根input字段，
不跳value中的任一输入，不增加私有认证标记。reviewer静审确认此边界后实际跑
[扩展after probe](review-evidence/retained_draft_inputs_extended_probe.py)：source
dialect、local schema、derived owner、body provenance、net evidence缺项五族
篡改全部ValueError；结合正式source/channel/capture/typed-spoof反例，关闭。
[原输出](review-evidence/retained_draft_inputs_extended_probe.after.stdout.txt)绑定
codec SHA `08f172f7e80ea56afbaf7a4d19391f9d5d44ba6e2a450adb154c61932933148a`。
原静默接受输出仍保留，新正常路径资源R3尚待，不冒记为R2已测修正成本。

### CR-11：malformed 相关输出先访问 property 而泄 KeyError（必须，已关闭）

contracts-r4实际16passed/1failed揭示中立Draft.channel_observations={}的encode
会从original.to_value→coverage泄KeyError('coverage')，而非明确ValueError。
reviewer同一真实捕获probe独立确认。原命令/source snapshot/stdout保留于
development/contracts-r4*，独立原输出见CR-10的before。

应在访问不可信original的派生property前比较其所有实际字段；只对正确重建
对象调用to_value，明确拒绝不一致。不得catch任意KeyError/TypeError冒充预期
资料错误，旧异常object/cause/context/suppression保持。

同一after独立probe将neutral channel_observations={}明确拒绝为ValueError，
不再访问其coverage property。修正没有catch任意异常；只在完整原字段比较成功
后对正确重建对象调用to_value。根据静审、正式修正验证及实际before/after关闭。

### EG-01：安装 smoke 对 mismatch 的 active 四边误用 normal 常量（工具，已关闭）

未参与工具实现的final_evidence_review专项发现check_body无条件断言MN0四边
20/20/20/20，但extraction_mismatch真实active.ymax64，BN.ymax90，第四边26。
这会使长矩阵后的源码外安装smoke必败。专项独立stdlib读取两GDS确认，并保留
原smoke全源/身份及before输出，见review-evidence/installed_smoke_mismatch_*。

执行者已按case保留精确断言，normal仍20^4，mismatch20/20/20/26，min均20，
没有删除或弱化检查。专项用原始GDS数值驱动小stand-in实际调用原check_body
与新check_body：原normal通过/mismatch失败，新两者通过。该工具问题关闭，
仍不是实际clean安装smoke通过，最终必须按指定矩阵实跑。

### CR-12：中立证据外壳未知版本可构造并编码却无法解码（必须，已关闭）

new graph guard查native/storage，body evaluator只查body.payload schema，未重入
EvidenceRecord外壳的schema_version/parser_version。reviewer静审提出候选后，
实际 [evidence_wrapper_versions_probe.py](review-evidence/evidence_wrapper_versions_probe.py)
以真实reader→W008/W009及原pure local builder构造中立输入（无完整W010 Result），
独立确认body两版本字段改unknown/999都可构造、encode约1.8MB neutral wire，
decode才因旧EvidenceRecord构造器拒绝。coherent local.rules同类两字段也如此，
破坏新中立DTO与codec的roundtrip合同。原输出
[before](review-evidence/evidence_wrapper_versions_probe.before.stdout.txt)绑定
domain d7654ce5… / codec08f172f7…。

同probe的derived两字段对照在constructor已被W013保护拒绝，未将该上游已有
防护误记为漏洞。body/local rules是真实新边界缺口，不改变旧classes/codecs；
建议在新graph原storage验证后统一重构保留SourceRef/EvidenceRecord并canonical
全字段核对，避免仅为body补洞漏其它owner。需保持合法class-default字段、
防复制隐藏alias、原异常历史；修后R4资源及最终新source验证待完成。

执行者在新`validate_terminal_graph`完成原native/storage全图检查后，收集保留的
SourceRef/EvidenceRecord；每个共享叶仅重构一次，以原public constructor核全部
字段，再做canonical比较。未在原壳调用`__post_init__`，未改旧DTO/codec；原
class-held init=False默认与extra存储分支保持。reviewer静审上述顺序后实际复跑
同一六项probe，body/local rules四个原漏项均在constructor明确ValueError
(`invalid evidence discriminator/version`)，derived两项对照仍拒绝；不再到encode
才丢弃坏外壳。见 [after原输出](review-evidence/evidence_wrapper_versions.after.stdout.txt)，
实际6.30秒，domain SHA
`5bb96a063ed41d708ed5322c1cb95ee2f1ce868c53b4b7158fcf2bfe79b7a731`，
codec仍`08f172f7e80ea56afbaf7a4d19391f9d5d44ba6e2a450adb154c61932933148a`。
据原反例实际复核关闭正确性finding；新guard正常路径成本仍待R4资源证据，
完整新source工程验证和最终review结论尚未通过。

## 其它独立核查（当前阶段）

- [body_math_probe](review-evidence/body_math_probe.py) 用800对1/20nm整数采样
  矩形、完整open-atom与对边线段独立判据核正面积、正长度、四边margin，全部通过；
  不调用产品union或fixture答案。[输出](review-evidence/body_math_probe.stdout.json)。
- [leaf_determinism_probe](review-evidence/leaf_determinism_probe.py) 在两个新进程
  `PYTHONHASHSEED=11/997`核新叶public encode/decode/digest与relation ref相同；
  小wire2642B，未重复构造捕获。[输出](review-evidence/leaf_determinism_probe.stdout.json)。
- [边界审计](review-evidence/source_boundary_audit.initial.json) 对方案提交逐字节
  核五个旧codec/认证源未变、tracked fixture无变化；新body/domain/aggregate/
  normalization/codec各自SHA归档。最终冻结后仍需核相同身份与实际diff全集。
- source.selected_cell malformed壳的早期`next`泄漏StopIteration风险已交执行；
  执行者改为明确ValueError且有正式反例，不捕获任意意外异常。此为边界提示，
  未出现接受伪造数据，不另立未复现的must。
- [结果审计](review-evidence/review_outcome_audit.stdout.json)按归档before/after
  自动核CR01–09所述实际变化，未重跑产品链。body关键after绑定
  `be59c340a021d9a9a3f25fa97729a8f2040c769522c9d36cbda6595377cad485`。
  此早期审计的计数标签保留原时点事实；CR08的“public漏洞”归因后来已明确撤回，
  不把未实际复现的gate漏洞列为已修产品缺陷。
- [CR10/11结果审计](review-evidence/retained_inputs_outcome_audit.stdout.json)
  独立读取并核原静默接受/KeyError与修后六项ValueError，无产品重跑。
- [CR12结果审计](review-evidence/evidence_metadata_outcome_audit.stdout.json)
  独立读取原六项before/after，核四项原roundtrip失败与两项上游对照、修后六项
  构造拒绝及当前domain/codec字节，14项通过，无产品重跑。

## 实跑、采信与限制

已实际执行上述叶存储、真实reader/neutral body、完整Result保留输入及metadata
before/after独立探针；各自绑定当时runtime SHA，不把早期输出改标成最终源。
body专项最终静审见[原记录](review-evidence/body-static-notes.md)，核全local/external
异型body pair、全部external taps、active/FRAME/唯一性、exact anchor后component
冲突、原local T05、八端与原差异边界，未发现新增must。新guard资源R4及clean
direct补测已由独立598项只读核验通过，见[资源review](resource-review.md)。
targeted-r6实际85passed/1failed为
ChannelSeed.source测试笔误，原失败保留。只改单点测试else分支后候选c7769fcb…，
独立[301项身份/前缀审计](review-evidence/candidate_r7_identity_audit.stdout.json)
确认runtime不变、85项通过前缀可按依赖/分支身份采信。剩余80现已实际通过，
source c7769fcb…不变；独立[冻结核验](review-evidence/resource_freeze_audit.stdout.json)
300项闭合286 selected live/Git commit字节、80实际后缀与85采信前缀，冻结提交
`66f5b1e5369549ed8df361f89f099acfd2f39e17`。资源clearance按精确source放行
双矩阵，实际最终工程通过及独立840项身份审计见上文。

- 本次独立实跑：归档的关键before/after反例、数学/存储/确定性/异常历史探针，
  以及只读资源、冻结、范围和最终工程审计；未参与被审实现/正式测试编写。
- 按身份采信：最终新冻结源双全量/typing/build/双clean安装；原W013资源reference
  保持803b4c4f…，新W014资源保持998aa805…，test-only delta采信到最终c7769fcb…。
  没有把不同source或原失败改标成一个通过suite，也未复制整套大wire/安装树。
- 当前范围审计[1356项原记录](review-evidence/authorized_scope_audit.stdout.json)
  确认PM要求/阶段/验收原段、architecture/roadmap/current-work、固定fixture/答案
  及8个旧codec源未改；两次提交均项目noreply。该时点的临时work副本后来整体
  迁移至`/workspace/work/w014-repo-scratch-20261113-final`，未当正式交付，历史URI
  与原证据未重写；迁移不影响冻结source或源码外安装输入。
- 未覆盖：完整M1、其它mandatory、通用PDK/S-D策略、真实EDA/LVS与生产准入、
  baseline/no_change/Stage6；U06仅具体设计，现reader仍要求body_context。
- 补跑触发：相关source/tests/config/依赖或输入改变、组合冲突、证据缺失/失配或
  新实证风险，按实际影响补验证；新产品源重新冻结后仍履行最终矩阵要求。
  仅文档/证据补记与换reviewer不触发重复双全量。
