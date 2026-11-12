# W013 独立代码、合同与证据 review

Reviewer：`/root/independent_review`，专项 `/root/independent_review/neutral_static_audit`。
均未参与 W013 方案设计、实现或验收测试编写。本文件保留 findings 原文，修正后由
reviewer 追加复核，不代写执行处置或PM验收。

## 初审范围与身份（2026-11-12）

受审runtime/config HEAD：`b42492fe32a70cf1819af21a9fe80f38edd43693`，相对
`aaa55cc081d16ff74ab51ec5a69149ca549363ed` 新增6模块、normalization公开入口与typing目标。
产品路径无staged/unstaged差异；当时untracked仅W013新资源/审查附件。
完整源码字节映射见 [初审source identity](review-evidence/code-static/initial-source-identity.json)。
新测试当时尚未集成；最终矩阵未启动，不能把当前runtime静态核查当成完整代码通过。

已独立读取新增全部runtime、旧公开codec/来源合同、现行layer/quality/trim owner及
方案修订。核查包括target/fragment、Fraction nm、union/coverage去重、原component摘要、
source-evidence/local scope、neutral与capture认证分层、旧wire Value子树及全字段比较、
原异常链、工程runner身份/冻结/双安装设计。当前root三路资源probe运行中，review未并发
构造captured W010/W013或执行重型回归，避免改变资源条件。

## Findings 原文

### CR-01：neutral draft 接受相互矛盾的 local operator bindings

**必须修正，开放。** `state/annotation.py:_validate_inputs` 验证node membership、
component ref、target/binding和unit，却没有检查每个保留ContactNode的`binding_ref`
与包含它的ContactComponent的`binding_ref`相同。`AnnotationBinding`也没有要求同一
原local topology的组件共享同一个operators owner。

独立最小反例是单个LI node，唯一component精确含其node ref，但node声称operators=A，
component声称operators=B。所有字段均由公开typed构造器建立；不伪造hash preimage。
其余refs明确作为neutral小值，不冒充capture认证。公开`AnnotationDraft`构造与新codec的
完整encode/decode roundtrip均接受这份内部矛盾图，见
[脚本](review-evidence/neutral-static/operator_binding_probe.py)与
[原输出](review-evidence/neutral-static/operator_binding_probe.stdout.json)。

脚本SHA-256 `a426361e7a95715a3e6579dfb1cce690354196d1e84d85b3d2ed52a725e4c713`；
原输出SHA-256 `c6ff216289281218893698878bc0f5c184b3fc63bbbb6afdf2206e677d87b322`。
实跑Python3.12.14，约0.26s，没有captured组件构建。调用：

```sh
PYTHONPATH=/workspace/Layauto PYTHONDONTWRITEBYTECODE=1 /workspace/work/w013-env/dev312/bin/python -B docs/tasks/W013/review-evidence/neutral-static/operator_binding_probe.py
```

W010的公开`LocalConnectivityDraft`本来要求所有nodes/components属于同一local binding。
W013保留两侧operator refs后仍须核内部一致，不能靠最终captured Result重建来代替neutral
公开DTO/codec自己的完整验证。该问题不要求neutral补齐其未保留的完整input，也不影响
已正常重建的captured Result，但不满足A5的公开完整验证与owner绑定。

修正要求：拒绝原topology内部多operators owner以及target node与所含component owner
不一致；补必要拒绝/roundtrip反例，并保持正常数据及原异常传播。执行处置由执行者填写，
关闭须由reviewer独立复核。

## 初期独立探针与已核事实

[精确集合探针](review-evidence/code-static/exact_set_probe.py)使用独立有限arrangement
oracle，160组随机输入、480项union/intersection/difference核查通过。覆盖1/20与1/7 nm
Fraction、负坐标及10^30偏移、冗余/重叠输入，核精确面积、覆盖、disjoint canonical输出。
它没有使用product同一算法生成预期，测试中的atom witness不是product的cell-center stamp。
原输出见 [JSON](review-evidence/code-static/exact_set_probe.stdout.json)。

该探针初次漏配PYTHONPATH，出现ModuleNotFoundError；原stderr作为
[attempt-01](review-evidence/code-static/exact_set_probe.attempt-01.stderr.txt)保留，修正调用环境后
exit0。neutral专项亦保留其首次导入路径错误；两者是review工具启动问题，不报作产品finding。

旧W007–W011 codecs当前未改；新Result从input派生，encode重新完整认证并比较compact全字段，
decode恢复原W010 canonical bytes走旧public decoder后重建并比较全字段。当前未发现该边界
直接跳过认证或篡改原异常链的静态问题，仍待独立captured错误路径探针和实际证据核验。

## 当前验证复用/未覆盖与结论

| 类别 | 本轮事实 |
| --- | --- |
| 实跑 | pure-neutral内部矛盾反例；独立Fraction集合480核查；runtime/config完整source identity；静态合同/codec/工程工具阅读 |
| 按身份采信 | 已关闭的方案门及旧输入/上游合同；尚未采信新产品最终矩阵，因其未执行 |
| 未覆盖 | 新测试集成、captured独立关键探针、三路成本完整身份及解释、双3.10/3.12新冻结全量/typing/build/双安装smoke |
| 补跑触发 | CR修正或其它runtime/test/config/依赖变化、证据身份不闭合、独立新风险；新冻结产品仍须要求的最终矩阵 |

**当前结论：CR-01开放，未完成代码review。** 本记录不改变PM阶段/current-work，不宣称
A1–A8完成或M1/EDA/发布验收，不要求因换reviewer而重复已同身份完成的全量。

### CR-01 追加变体：同一local/effective图混入多个operator owners

在同一受审 `b42492f` 上，专项另以两个LI nodes复现两种内部owner矛盾，均被公开Draft
及codec完整roundtrip接受，见 [multiple_owners_probe.py](review-evidence/neutral-static/multiple_owners_probe.py)
与 [原输出](review-evidence/neutral-static/multiple_owners_probe.stdout.json)：

1. 所有ContactNode/ContactComponent的local operators ref相同，但两个target的
   `node.region.operator_ref`不同；它们却共同声明同一个`AnnotationBinding.effective_ref`。
2. 所有region operators ref相同、每node与自己的component也相配，但不同components/nodes
   分别声明不同local operators ref；它们共同声明同一个`AnnotationBinding.local_ref`。

脚本SHA-256 `cebb09a93fdb8062a02459858170a4f8383ac5bff3aba9d5ebf059c39db30600`，
原输出SHA-256 `e9a5e10dbaac4b7813e0fae5aa99cd1b61de1a2f67816ab46de94ecac27a88dd`。
实跑约0.63s，不含captured构建。W010所有nodes本就由同一effective operator binding生成，
同一retained local/effective graph应验证其operators owner一致。请并入CR-01修正及拒绝测试；
不要求neutral验证其没有保留的full capture。原单node反例不改写，CR-01仍开放。

### CR-02：新公开边界接受带可写 backing 的 forged FrozenMap

**必须修正，开放。** `MatchEvidence`直接保留传入的精确type `FrozenMap` policy；
`common`/现用`validate_closed_graph`只遍历map.items，未核map内部storage确为冻结tuple。
新neutral encode虽重进公开构造，也继续接受这类原对象。

独立 [map_backing_probe.py](review-evidence/neutral-static/map_backing_probe.py) 用
`object.__new__`/`object.__setattr__`构造精确type FrozenMap，其`_entries`指向外部list。
该malformed叶值被`MatchEvidence`构造和新codec接受；外部`backing.append(...)`后，原DTO的
policy内容、content ref和canonical wire均改变，见
[原输出](review-evidence/neutral-static/map_backing_probe.stdout.json)。这是新A5边界承诺的
“拒绝伪造/防御快照/无可写alias”反例，**不是**安全FrozenMap公共构造器本身保留alias，
也不要求重开旧通用codec性能任务。

修正要求：在W013新公开DTO、neutral/result codec和完整retained input认证入口，拒绝
带不合法/可写storage的map图，或建立不会保留外部可写alias且不隐藏非法字段的防御快照。
不能只检查一个MatchEvidence.policy字段，而让同类malformed叶值经其它retained maps进入；
保持旧codec wire/ref和原异常链。补原反例及nested map/backing拒绝、正常合法map路径，
由reviewer复核。当前已实证neutral路径；captured路径可能面临相同检查机制，尚未为此
并发运行captured重型探针，后续按实际风险补核。

本例Python3.12.14，约0.17s；runtime身份仍为b42492f。全部专项脚本/输出/导入路径失败和
源码hash由 [neutral专项manifest](review-evidence/neutral-static/manifest.json)绑定，
[README](review-evidence/neutral-static/README.md)明确各反例范围。CR-01/02均开放，
当前不支持最终代码通过或启动最终产品验收结论。

### CR-02 追加实际 captured input 反例

三路资源检查结束后，reviewer串行补一次真实W005→W010→W013 direct构建，无完整W013
wire roundtrip，约23.77s。将原retained `ParseResult.value` FrozenMap的storage改成同内容
外部list（没有修改任何逻辑字段/源字节、没有patch codec/validator）后，新public Result
仍构造为success并保留原input。外部append可改变`result.input`中的原证据，status仍success。
因此CR-02不只影响单独neutral MatchEvidence，也影响新Result完整retained input边界。

[独立脚本](review-evidence/code-static/captured_map_alias_probe.py)
SHA-256 `2ace848ddee7c6a1920f8d5bc1a5827ef786f6204b51c7e476012af48d9e934a`；
[原输出](review-evidence/code-static/captured_map_alias_probe.stdout.json)
SHA-256 `4527c167d1ff1535b37a75e99fb61bbfb1bea5a8244cd15043288873c24c4af3`。
输出HEAD是`a347263a4ed26a08e69dcb5004669408e961728d`（其间只集成新测试），已另核
`b42492f→a347263`的runtime/config无diff，故本反例受审runtime仍为原b424身份。
原失败不覆盖；修后须从完整新input认证入口在复制前拒绝该malformed map，不改旧codec。

### CR-03：retained target角色与region provenance未完整闭合

**必须修正，开放。** 对执行者提出的两个已有字段一致性风险作独立验证后，确认新neutral
公开聚合仍接受如下矛盾；不要求它认证未保留的full capture或重做W009算法。

**(a) 非导体classification仍可成为导体target。** 保留一个M1 ContactNode/target，
同时用合法schema的synthetic drawn owner声明M1.role=marker或contact，并同步将原record的
classification改为marker或connector。`AnnotationDraft._validate_inputs`最后只比较
layer/rectangle/source，不检查target record必须是target_conductor。公开Draft构造及codec
roundtrip接受，导体coverage分母仍计该target的10nm²，与保留role/category矛盾。

原脚本 [target_classification_probe.py](review-evidence/neutral-static/target_classification_probe.py)，
SHA-256 `50fc4dd0476e821f66a35c9185a0fb7dd5c5a227f0ccc536d4042ebd3d927e7e`；
[原输出](review-evidence/neutral-static/target_classification_probe.stdout.json)
SHA-256 `e5bbedfc4acbe1ef1f7c78aefaad0e4aaf63a151fab95a219719515d75be8e0a`。

**(b) region contributors可指向不存在的drawn记录。** 保留LI region，其contributors含一个
不在`binding.drawn_record_ids`或完整classifications表中的CUT ref；其它operators owner已一致，
公开Draft和codec仍接受。owner_id有闭合检查，contributors这条来源边缺失对应检查。

原脚本 [contributor_closure_probe.py](review-evidence/neutral-static/contributor_closure_probe.py)，
SHA-256 `9512d0a465cbbd15a5f6ebc4526e020b3f309edc2a7bdaabf0214fbab3e59696`；
[原输出](review-evidence/neutral-static/contributor_closure_probe.stdout.json)
SHA-256 `cddfca939aef13f350231646d3a687b67d1ee27345b5925e6c8302b9583e7c02`。

首两例在`e8f375a`上的公开构造/codec均接受。为闭合并发修正的精确身份，另用
[独立原probe harness](review-evidence/code-static/run_neutral_rechecks.py)在
`85299a1d20ba5a2b6d9e677653b527c49d92f21b`与当时normalization两个文件的工作区补丁上
重新运行两份**原脚本**，均再次接受；完整8个runtime/config SHA、工作区patch、命令、
原stdout/stderr、修前后source稳定检查见
[cr03-before/receipt.json](review-evidence/code-static/cr03-before/receipt.json)。
该次两个pure probes合计约0.6s，source_stable_during_probes=true，无captured构建。
原e8输出保留，不用后来的source hash冒记原测试身份。

修正要求：拒绝target对非target_conductor记录的引用，确保现有layer/role/classification与
node/target关系内部一致；target region的全部contributor IDs必须在该draft保留的drawn
identity/classification集合闭合。保留空CUT结果、正常导体/marker/connector分类及合法
多contributor来源；补必要失败/正常反例，reviewer独立复核。CR-01/02修正尚待整体复核，
CR-03本身也未关闭；新源最终freeze/matrix仍不可冒用旧身份。

## CR-01–03 修后独立复核（2026-11-12）

受审修后runtime/config为`10b1f0fc6973e3957046badf7b8e107be88f6476`，后续
`119189d5a958b617fe754b61c4e3b8a7e8a9f9fb`仅补入CR-03测试，runtime/config相同。
本次actual source/test/config映射见
[postfix-source-identity.json](review-evidence/code-static/postfix-source-identity.json)，
各独立probe另外保存8个受影响runtime/config的SHA并核其执行前后稳定。
原findings、原接受输出与原资源证据全部保留。

**CR-01关闭。** `AnnotationBinding`拒绝多contact operators owner；draft核每node与
所在component owner相同、全target共享同一effective region operators。独立执行原三种
owner反例均ValueError拒绝。正常小target构造和canonical roundtrip通过，不是统一拒绝输入。

**CR-02关闭。** W013任务专属guard核原FrozenMap tuple backing/entry/key唯一性、native
value、Fraction规范性、value-only上下文与cycle；四core模块及Result/codec在复制前使用，
旧通用validator/codec保持未改。独立原mutable alias反例、nested mutable map、重复key、
list entry、cycle、missing backing、共享tuple跨value-only上下文和伪造未约分Fraction均拒绝。
实际captured旧input backing在builder、public Result constructor和encoder三入口均在
原copy/重建前拒绝；safe policy和正常capture仍可构造。

**CR-03关闭。** target须对应target_conductor分类；region全部contributors必须在完整
retained drawn表中，LI→CUT/OD→POLY/其它无contributors的来源角色按既有有限operator检查。
原marker target、connector target、dangling contributor分别ValueError拒绝；不重算或改动几何。
静态核新回归测试只对该内部关系收口，没有扩展输入或旧fixture。

纯neutral复核共14项拒绝及两个正常roundtrip见
[postfix_neutral_recheck.py](review-evidence/code-static/postfix_neutral_recheck.py)与
[原输出](review-evidence/code-static/postfix_neutral_recheck.stdout.json)，Python3.12.14，约0.42s。
脚本SHA-256 `2c07b019859ddbb38dd70eb2a620dba95f8ae39bc9ff1b38324d8c89a6590ac2`；
输出SHA-256 `d317ff583f7e7a2bc6920200d245e8b9f2e86d15a68f16ec71494d34e945d83e`。

实际direct构建及原异常链复核见
[postfix_captured_recheck.py](review-evidence/code-static/postfix_captured_recheck.py)与
[原输出](review-evidence/code-static/postfix_captured_recheck.stdout.json)，约28.46s：
正常14nodes/8edges/6components，直接覆盖3170、未覆盖31920、目标总35090nm²；OD/BODY仍无
直接query覆盖，MARK保留。另在旧public decoder入口独立注入RuntimeError/ValueError/
KeyboardInterrupt/SystemExit，分别覆盖builder/constructor/encoder/decoder，原object、cause、
context及suppression全部不变。异常packet保留完整真实旧input Value，故障注入发生在其
原public decode，故意不可达的compact输出不作为成功wire roundtrip证据。
脚本SHA-256 `3c080bf55df562d1ba5aea85e06a8b973be6936b1be2f456acaa8501f6e69933`；
输出SHA-256 `d4aa85500b61b026033cb8c6dbf2e75af70e9a8bfc6040aa5c5ef87a5e8301a2`。

域模块新增guard后，独立精确集合480项以同一原脚本在新源再次通过，原输出另存
[postfix_exact_set_probe.stdout.json](review-evidence/code-static/postfix_exact_set_probe.stdout.json)，
未覆盖原b424版本结果。新development `run_check.py`已静态核源码完整before/after映射、
实际argv/cwd/env、原日志hash/返回码与禁止覆盖旧attempt；它只是开发回执，不能替代最终矩阵。

**本轮代码/合同必须修正项0，支持继续既定范围的资源与最终工程验证。** 这不是最终完整
review通过：修后同源三路成本、最终新冻结双3.10/3.12全量/typing/build/双干净安装源码外
smoke及其证据身份仍待核验。按身份采信已有原合同与同源实跑，不因本reviewer换角色
重跑无关完整矩阵；若产品/测试/config再变，按规则重新冻结并核受影响结论。

## 修后资源检查点独立review（2026-11-12）

核查原证据 [resource-attempt-04/suite.json](resource-attempt-04/suite.json) 及其冻结probe、
三份case/command、原stdout/stderr。未重复产品捕获或为换reviewer重跑完整组合。
独立审计脚本 [resource04_identity_audit.py](review-evidence/code-static/resource04_identity_audit.py)
SHA-256 `5e30140db4a08bc3d819e98dd0042ee352cd2aa2694960a5b5c62967c93c5770`；
[审计原输出](review-evidence/code-static/resource04_identity_audit.stdout.json)
SHA-256 `7e07ee301c9c4df980456e073010c9e6e1c422b107148dde7e4aacbd0d8a79e0`，exit0。

三路source_id均为
`6463eb67b1c1ce5b9fd1fca436fa499a4ad14da004ef8fcd913872bd350443a9`，273个实际源码/测试/config
文件映射与本review修后快照、当前字节及开发`110 passed`回执完全一致。逐hash核实际31个
capture sources×3、原固定mismatch URI的35项文件、116份已验收fixture；probe副本hash、
命令与原输出hash闭合。readback沿用原RunRequest/URI/cache/roots/GC，attempt/checkpoint
不推进、无terminal；主路径没有W011 Result构造。所有旧codec/fixture均未为此改写。

| 固定case | 完整wire B | 相对内嵌旧W010新增B | 峰值KiB | 新public build+encode+decode秒 |
| --- | ---: | ---: | ---: | ---: |
| normal-direct | 23,104,092 | 314,874 | 204,668 | 54.58 |
| normal-readback | 59,736,484 | 315,538 | 518,612 | 112.81 |
| extraction-mismatch | 23,104,160 | 314,878 | 205,364 | 54.34 |

三个case的旧/新wire SHA均与修前resource03相同；direct内嵌旧W010 wire SHA还与同机独立
W010 baseline相同。新wire没有整包hex倍增，也未将完整旧input换成不可认证ref。
实际观察已有调用确认每路W010 public decode为build/encode/decode的1/1/2次，共4次；
direct这4次inclusive47.59s，neutral draft重建3次合计2.40s。其余还包括旧encode、完整Value
解析/canonical化、来源digest与native graph检查，新增成本有具体归因。`_require_input`
包含其中部分旧decode，**nested inclusive buckets不相加**；没有用旧W011跨环境秒数
宣称稳定收益，也没有删认证、扩状态链或重开A2/B。

**资源节点通过，无必须先交PM的重复序列化增长、资源阻塞或未解释成本。** 支持在同一新冻结
source_id上启动要求的双3.10/3.12、各1731项最终矩阵。16GiB/4CPU下两pytest并行可作为调度
安排，package与两安装smoke等两矩阵完成后串行；这不是单次产品成本改善或最大pytest/生产
输入资源保证。出现实际资源失败时保留原日志并按风险调整，不能把中断/部分矩阵记作完成。

本次实跑只有证据/输入hash审计；产品三路原实跑按精确身份采信。尚未覆盖最终双全量、typing、
build、双干净安装源码外smoke及其包/环境/源身份，**完整review结论仍待这些证据**。
后续仅文档补记不触发重跑；runtime/tests/config/依赖或证据绑定变化则按规则核影响并重新冻结。
