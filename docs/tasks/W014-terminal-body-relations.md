# W014 — 器件端子与外置 body 关系核对草稿

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W014；把已定位器件、局部物理分量及网络证据连接起来，逐端核对 source CDL 的 D/G/S/B，并单独证明现行 synthetic 外部 body 关联 |
| 里程碑 / 依赖 | M1 Stage 2；W007 source/device/net identities，W009 channel/terminal regions，W010 local graph，W011 channel identity/FIN，W013 net coverage。仍不完成整个M1 |
| 授权 | 2026-11-13用户在W013验收后要求继续推进；沿用独立执行session、先具体方案及独立review、完成交PM的方式 |
| 恢复 | 从main `00ee6c6f51b683a8aefa96a5415b7ca969778502`（W013验收补记）准备；执行分支 `codex/w014-terminal-body-relations`，接手该分支最新PM准备提交。产品冻结仍为W013的`2a45938`，不得带入W012 A2候选 |
| 阶段 | **可执行：先方案与独立方案review，必须项关闭后在既定范围实施。** 未实现、未跑产品测试，PM准备不代替方案review |
| 允许写入 | v2内最小中立DTO、annotation/derive只读关系逻辑、必要normalization认证入口/codec及相关测试；本任务执行/方案区和`docs/tasks/W014/`。具体文件表由执行方案确定 |
| 非目标 | 不改已验收fixture/答案、旧wire合同或历史证据；不实现全套工艺坐标、通用DRC引擎、color/pin-access全覆盖、跨cell routing、baseline/publication、ECO、Stage6或真实EDA。U06生产可选输入本轮只出具体方案，不改变现行reader必填body_context |
| 架构依据 | 基线main的[architecture](../architecture.md) §2.3、3.3/3.6、4.5–4.7、5.6–5.9、11.2/11.5/11.9/11.15；[roadmap](../roadmap.md) R06/R07/R12/R16、[U06](../roadmap.md#production-body-evidence)；[验证复用](../collaboration/rules.md#verification-reuse) |
| 分工 | 执行提出方案、实现及证据；未参与对应设计/实现者独立review；PM核验、集成及最终验收。入口见[执行prompt](W014/execution-prompt.md) |

### 为什么现在做

W011已能把query器件身份定位到channel并计量FIN，且保留局部G/S/D topology；W013已能给既有局部分量关联网络并报告直接区域覆盖。本轮补上“这个器件的这个端子，实际关联的网络是否等于source CDL”的关系层。它有明确的已有输入与独立答案，可以推进到完整Stage2状态的构建；不能把六个局部端关系一致直接称为完整器件抽取或LVS通过。

现行`tech/physical.json`的`toy_device_terminal_context/2`明确左端S、右端D、ordered D/G/S/B、禁止S/D swap和device reduction；不是所有PDK的通用假设。`body_context/2`规定独立外部几何链，其关联不能改变本地physical graph。具体规则阈值来自同源`tech/rules.json`，不能抄固定答案到产品代码。

### 正常小样张与事实层次

以下来自已验收`tests/fixtures/w003_m1/source.cdl`、`tech/physical.json`、`tech/rules.json`、raw query及独立`oracle.json`，不是产品输入；精确目标身份/字段由执行方案定义。

| 器件 | D | G | S | B |
| --- | --- | --- | --- | --- |
| MN0 | ON.D → Y | gate关联 → A | ON.S → VSS | BN局部分量仍unknown；BN → BN.ext → TN.ext → MN.ext → MN的独立context关联 → VSS |
| MP0 | OP.D → Y | gate关联 → A | OP.S → VDD | BP局部分量仍unknown；BP → BP.ext → TP.ext → MP.ext → MP的独立context关联 → VDD |

必须分列：CDL期望net、几何端子/本地component、query证据关联net、外部context关联net、判定及来源。共享POLY作为两个器件的gate conductor是正常关系；不能把整条POLY都唯一归某个device，也不能把source的期望net写成已观测net。顶层CDL端口名已知不等于已经定位物理pin access；本任务不新增该承诺。

正常保留14本地nodes、8edges、6components；两个body分量仍不与电源分量本地union。外部6图形作为只读context，不进入本地layout/occupancy/导出。`production_matched_body_evidence=false`、`LVS not_run`保持。几何连接事实、包围规则结果、网络关联和整体比较状态分别表达。

| 验收项 | 输入/条件 → 预期行为 | 独立依据与验证 |
| --- | --- | --- |
| A1 同源组合 | W011器件/端区、W013标注和body/tech来自同一captured输入、local/effective/geometry、run/database/top/unit/profile → 可组合；跨来源、伪造/遗漏/冲突owner或来源链拒绝 | 核生产者/消费者两侧合同；同值不同来源、换run/tech/region、改变后几何旧ref等反例。不得仅比名字、任意摘要或一项hash |
| A2 六个本地端关系 | 依真实device identity/channel及既定ordered policy定位D/G/S；正常两器件的6个端逐项与source一致；共享gate保留两device关系但不制造collision或整shape独占 | 上述小样张及现行oracle的本地投影；网络证据不足→unknown/indeterminate，多个冲突net→conflict，确有不同net→mismatch，不猜网、不调换S/D消除错误。物理拓扑不变 |
| A3 外部body几何证明 | 从绑定实际source GDS/top/FRAME/对象/单位的现行context重算两条body链；同类型唯一local body包围对应active、同类边界正长度连续、tap正面积接触唯一external body与rail、rail唯一连续到local M1，最后关联query网络 | 原body_associations、tech声明及独立手算；查询/声明中的expected_semantic_rail只是待核主张。无本地tap的正常样本必须成功建立context关联，不能要求把tap放进主GDS |
| A4 body规则与八端比较 | 核T04现行全部body子条件、T05外部tap enclosure，保留W010本地T05结果；八端D/G/S/B按T08授权语义比较。几何链存在但包围不足必须单列，不等同已满足body规则 | 阈值取同源rules。正常两域active enclosure为20/10nm、tap body enclosure8/8nm、rail enclosure2/2nm，详见oracle；独立审计覆盖全体适用对象，不只遍历输入指定的成功链。未覆盖其它规则，不宣称完整mandatory通过 |
| A5 错误与精确性 | 既有7个新增body见证及缺operator/context、错误body/rail类型、断开、歧义、绑定、包围不足按实际到达的边界拒绝/定位；完整保留已读证据。45.05nm等精确值不得取整误配45nm，边/点与正面积区别明确 | 映射现行failures及W004 REQ-01回归。reader已拒绝的案例记录原边界，不伪装成已到W014；W014组件不自行终结run或伪造sealed阶段。未知不是错误资料的降级出口 |
| A6 完整性与有限比较 | 每个已准入source device的D/G/S/B均有记录或定位缺项；保留原W011 FIN/参数差异和W013coverage/conflict。既有extraction_mismatch仍为4对source5，不能因端网络一致升级为整体匹配 | 正常、端net mismatch、unknown、冲突、缺/重复device/terminal及已有mismatch组合；记录比较范围，不宣称完整model/VT、完整抽取或no_change |
| A7 DTO/公开认证与资源 | 新草稿不可变、无可写alias，完整字段/来源/owner闭合、canonical roundtrip/ref、异常object/cause/context/suppression保持；旧wire/ref及认证合同不变 | 公开入口与neutral构造分别验证；不能用临时私有“已认证”标记绕过公开认证。方案画共享输入及重建次数，避免把两份完整W011/W013 Result再套一层；最早direct/readback/mismatch组合测耗时/峰值/wire及新增量，显著放大在最终矩阵前交PM |
| A8 U06具体设计交付 | 对“仅底层cell、无本地tap/无外部上下文”给出具体输入→输出→可继续操作/被阻止操作方案；区分已知本地端口和内部net、未知父级/global supply关联、未证明body物理路径、错误已提供证据 | 交`W014/production-body-scope.md`，至少包含缺上下文、可信替代证据、仅人工标注、错误绑定四类小样张，列最小所需资料及后续实施边界。当前仅方案，不能宣布reader已支持省略body_context；实质新格式/承诺由PM按既有用户授权判断，必要时带具体选择交用户 |
| A9 工程与review | 先方案review，再实现/独立代码review；开发新增/受影响，最终冻结双3.10/3.12全量、typing、构建及双干净安装源码外三路smoke。完成交PM，不自行验收或合main | 按默认验证复用，保留原失败/修复复核；受测源码/测试/config/依赖/输入/原命令与输出可核验。review只补独立关键反例和缺口，不为换session重跑双全量 |

### 执行方案必须先收敛的内容

1. 调查W011 `ChannelIdentityDraft.associations/topology`、W013 component/fragment evidence、现行body capture与tech/rule所有权。列可直接复用、需适配和不能直接借用之处；`tests/support/w004_body.py`及legacy仅参考，不能成为runtime依赖或唯一正确性依据。
2. 给出最小公开输入/输出、所有权、target identity、source与observed的区分、状态/错误与上游失败保留方案。A1–A7中未确定的内部实现选择由执行/review解决；新增物理解释或输入合同不能凭本任务标题自行定义。
3. 完整本地与外部scope的边界；T04/T05/T08事实和判定覆盖表。先确定缺口/多义/错误的具体输出，再实施。不要为展示八个端子重写通用rule engine或初始化事务。
4. 资源调用图、最小重建/序列化方案、三路早期检查和工程验证计划。W012 A2已停止，不能顺带复活其改动或跳过来源认证；旧完整矩阵与大wire仅引用原身份，不复制同一封包。
5. A8的生产场景方案可与既定synthetic实现并行整理；不依赖未知生产资料才能完成现行toy关系核对，但若发现二者有合同冲突，带最小反例交PM，不暗中改必填字段。

## 方案与决定（执行准备，PM接收）

执行方案见 [plan](W014/plan.md)、[body调查](W014/body-design-notes.md)；
未参与设计的 reviewer 已完成 [独立方案review](W014/plan-review.md)，
PR-01/PR-02修正复核关闭，剩余必须项0。方案与review冻结提交
`40559e0186f7d80bb8a7f3256c900e0fadd66191`。
[U06具体方案](W014/production-body-scope.md)只作为设计交付，未改变现行reader
或生产格式；D1=A不重复询问。后续代码review、最终工程验证及PM验收分别完成。

## 执行结果（执行）

2026-11-13执行恢复：目标分支实际准备head为
`8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4`，原工作区干净；产品仍为已验收
W013，未带入W012 A2。先完成具体方案和独立门review，随后实施授权范围；
产品、测试与配置冻结于`66f5b1e5369549ed8df361f89f099acfd2f39e17`，完整
source_id为`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`。

实现、A1–A9覆盖、原失败及修复链见[执行证据](W014/execution.md)。开发165项
范围已闭合（85项按单测试分支delta采信、80项最终候选实跑）；最终资源三路经
[独立资源review](W014/resource-review.md)核证。双3.10/3.12最终全量各1889
passed，保留原1731 IDs；strict typing各65文件及wheel/sdist build通过，完整
111项runtime字节一致。双clean安装源码外三路smoke全部通过，21条实际命令
均exit0，检查后冻结源身份复核一致，见[整体回执](W014/verification/receipt.json)。
未参与实现者的[最终工程审计](W014/review-evidence/final_engineering_audit.stdout.json)
实际840项通过，未重跑产品链；代码review结论由reviewer填写下节。

交付保留正常八端有限关系、原FIN差异及coverage/conflict；本地graph和unknown
body分量不变，无baseline/terminal/真实LVS或生产准入承诺。A8四类生产样张见
[U06方案](W014/production-body-scope.md)，仅设计，reader必填不改。原失败、
修复复核、三路资源、实跑/采信/未覆盖/补跑触发均见执行证据，交PM核验接收。

## Review结论（reviewer）

独立review通过，未关闭必须项0，交PM验收。被审产品冻结为
`66f5b1e5369549ed8df361f89f099acfd2f39e17`，完整source_id
`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`。
Reviewer未参与实现或正式测试编写；完整A1–A9核查、独立反例及限制见
[代码review](W014/code-review.md)。CR01–07、CR09–12共11项复核关闭；
CR08的公开链缺口归因已撤回，EG01工具问题由实际双安装smoke验证关闭，
原finding、失败与调查纠正保留。

最终工程证据由未参与实现者独立只读审计，
[840项通过](W014/review-evidence/final_engineering_audit.stdout.json)：
双3.10/3.12各1889 passed（保留原1731项）、strict typing各65、build、两包和
双clean安装各111 runtime字节、源码外三路smoke及21条原命令/log/hash/时间、
286项Git/live/tar冻结身份均闭合。按身份采信已有矩阵，未为换reviewer重复跑。

正常六个本地端与两个独立body关系、完整性/精确性/错误边界及有限比较符合
本任务授权；本地graph未union，BN/BP仍unknown，原FIN4对source5与W013缺口
保留。U06仅具体设计，现reader的body_context必填未改；未声明完整M1、全部
mandatory、真实LVS/生产准入、baseline/no_change或Stage6。此结论不代PM验收。

## PM验收与交接（PM）

2026-11-13：PM对照架构、W011/W013实际接口、source CDL、现行physical/rules、oracle/body context及W004 helper，选择端子与外置body关系作为下一切片。U06本轮必须形成具体设计，但生产可选输入尚未授权为本轮实现范围。本次只准备任务和恢复入口，不改变runtime、fixture、旧协议或验收答案，未运行产品测试；只核文档链接、范围及Git身份。

下一执行session按[执行prompt](W014/execution-prompt.md)先具体方案及独立review，再按门条件实施并交PM。完整M1/生产验收继续保留后续节点。
