# W014 / A8 — 仅底层 cell 的生产 body 处理方案

本文件是交 PM 的 U06 设计材料，不是已实现的生产入口、输入格式或验收结论。
现行 W005 synthetic reader 仍要求 `body_context`；未提供时仍按现行合同返回
`RequiredBodyContextUnavailable`。W014 不增加省略开关，也不把现行 toy JSON
规定为所有生产 profile 的必需资料。

依据：[U06 场景与验收方向](../../roadmap.md#production-body-evidence)、
[架构 §3.6](../../architecture.md#36-connectivity-state-作为拓扑解释层)、
[§5.6–5.9](../../architecture.md#56-per-region--fragment-annotation-overlay)、
[W014 A8](../W014-terminal-body-relations.md)；synthetic D1=A 已确定，
见 [W004 PM1](../W004-fixture-revision.md)。本方案不重新选择 D1。

## 推荐处理方式

后续生产适配把“用户没有选择外部证据”与“所选证据错误”分开处理，按本次操作
需要的事实检查能力，而不是给整个 cell 一个笼统的 body 通过/失败标志。
保留来源已闭合的本地语义、几何、拓扑及 query 关联；分别报告父级连接是否已知、
body 物理路径是否已证明、已提供证据是否有效，以及哪些操作仍缺必需条件。

首个生产适配任务应先提供明确的读取/分析入口，允许在缺外部关系时取得本地事实
及定位缺项；完整运行入口则逐项执行所选 profile 的 mandatory 要求。缺失必需
body 证明时阻止相应准入/修改/发布，不能把 mandatory 改成 deferred 来取得成功。
新入口、具体格式与状态编码应由后续任务提出样张、独立 review，并由 PM 按授权
确认；本文件的逻辑字段不构成新的 parser schema 或 wire 合同。

建议报告至少保留下列相互独立的事实：

| 事实 | 最小内容 | 不能据此推出什么 |
| --- | --- | --- |
| 本地语义 | source CDL 的 cell、端口、内部 net、器件 ordered D/G/S/B 与 source ref | source 声明不是观测到的导通，也不是父级/global supply 连接 |
| 本地观测 | 版本绑定的 exact region、local component、query net 关联、coverage/conflict、未标注区域 | 端口名不证明物理 pin access；同名不建立 scope 外 edge |
| 父级关系 | 明确 instance path 下的 child pin→parent net→global/voltage domain 映射及证据 | 供电角色或 pin map 不证明 body→tap→rail 的物理路径 |
| body 证明 | 绑定的 body/active/boundary、所选 profile、路径或冻结依据、适用 scope、规则检查和证据 ref | 几何链存在不等于 enclosure 等全部规则通过；toy 成功不等于生产准入 |
| 缺项与错误 | 未选择/缺文件/格式错/错绑定/违例分别定位；指出受阻操作 | 错误证据不能静默按“未提供”处理；违例不能改成 unknown |

## 四类输入与输出小样张

以下是后续生产适配的逻辑样张，单位和 hash 是示意身份，不是可直接提交给现行
reader 的输入。共同底层 cell 为 `INV_LEAF`，用户只交该 cell 的 source GDS/CDL
和同源 query。CDL 声明端口 `A Y VDD VSS`；`MN0=(Y,A,VSS,VSS)`、
`MP0=(Y,A,VDD,VDD)`，顺序为 D/G/S/B。query 与 exact 本地几何能支持六个
D/G/S 关联，两个本地 body component 未有 net 关联。所有“本地已知”仍以真实
profile、来源认证和 coverage 检查成立为条件，不从本样张常量生成产品答案。

### 样张 1：没有选择上层或 body 资料

输入：`INV_LEAF@layout-h1`、`source-cdl-h1`、`query-run-17`；没有父级 instance、
pin map、global 定义、本地 tap 或外部 body 证据。用户目的为查看本地几何与端子。

| 输出位置 | 结果 |
| --- | --- |
| 本地 source | 四个端口、source net membership 和八个端子期望均保留 |
| 本地 observed | `MN0 D=Y/G=A/S=VSS`、`MP0 D=Y/G=A/S=VDD` 及各自 region/component/query ref 保留；B 观测未知，不抄 source 的 VSS/VDD |
| 父级/global | instance 未提供；`INV_LEAF.VDD/VSS` 的父级 net、global 角色及电压域均未知。不能凭名字认定 parent VDD/VSS |
| body | `MN0.B`、`MP0.B` 外部物理路径未证明；缺上下文，不据此判 cell 几何错误 |
| 比较范围 | 可报告六个本地端的有限一致；B 比较不确定，保留其它参数差异、coverage/conflict，不能汇总为完整抽取匹配 |

可继续：解析与来源检查、本地几何/连通/FIN 计量、局部标注和覆盖报告、
不依赖外部关系的规则检查、只读定位，以及明确标为未提交的候选影响分析。
这些结果分别报告实际成功/差异/错误，不能把 body 缺项清空已知本地事实。

须阻止：依赖父级电源/电压关系的 rule exemption、body complete、完整 T08/
LVS/mandatory 通过、生产准入、baseline/no_change/成功运行结论，以及没有合法
body/boundary 证明的实际几何修改或发布。候选图不能冒充可执行授权；未知几何
仍按保守策略保留为 blockage/suspect，不能当成与任意网兼容。

### 样张 2：没有独立 tapcell 文件，但有可信替代证据

输入仍是上述底层 cell；另提供由 profile 认可的 matched baseline 提取证据
`extract-42`，绑定 `layout-h1/source-cdl-h1`、model/deck/tool/profile 版本、
提取 completion/match、被覆盖的 body/active/边界对象和必要层级 scope。
若要解释父级供电，还提供 `TOP/U7` 的 instance/pin mapping：
`U7.VDD→PWR1`、`U7.VSS→GND1`，并附 global/domain 声明。

推荐优先研究架构允许的 **baseline LVS＋body/boundary invariant** 冻结路径。
该路径需要 profile 明确实际检查哪些 body 关系、所覆盖边界/halo 和允许变化集，
并证明每个候选都保持这些条件；不能仅凭一行“LVS passed”，也不能仅凭
“没有直接编辑 tap”认定不影响 body。若可信工具证据无法绑定当前 region、
证明相关 body 语义或完整 scope，就仍保留相应缺项。

| 输出位置 | 结果 |
| --- | --- |
| 本地事实 | 六个 D/G/S 和 source 事实保持；本地 body component 不新增物理 union |
| 父级/global | pin map 经绑定检查后可报告 `U7` 的 PWR1/GND1 及 domain；没有 map 时此列继续未知，不妨碍独立评估 body 证据 |
| body | 在 `extract-42` 的受信范围内报告 baseline body assurance 与冻结条件；它不声称已经从缺失几何重建外部 tap 链 |
| 操作许可 | 仅能考虑 profile 明确允许且逐项满足 body/boundary invariant 的操作；其它 mandatory、生产准入和候选验证仍各自必需 |
| 证明失效 | 编辑 active/body、边界、相关导体/连接、层级变换或任何提取依赖，超出已证明不变量时，使受影响 assurance 失效，要求重验或拒绝 |

另一个可研究的替代是仅交受影响边界附近的**最小几何窗口**，覆盖从本地 body
到 tap/rail 及必要 local pin 的完整路径，带原坐标/变换/对象身份和 tech/operator。
不要求提交完整父级版图；窗口边缘若仍截断了待证明关系，必须继续定位缺项。
它与冻结路径的证明内容不同，后续 profile 必须声明采用哪种路径及各自完整性条件。

### 样张 3：只有人工标注的供电意图

输入另附标注：“`TOP/U7` 的 VSS 接 GND1，MN0.B 应接 GND1；VDD 接 PWR1”。
记录作者、时间、scope、当前 source 身份及其声明性质；未附受信工具报告或路径几何。

输出把这些内容放在**人工声明/预期**列，可用于人工定位、请求最小资料、约束
候选意图。它不覆盖 query observed net，不改变本地拓扑，也不单独证明父级
实际连接、电压域、tap enclosure 或 body/rail 导通。缺少证明的列继续未知，
与样张 1 相同的依赖操作仍须阻止。若未来 profile 接受人工输入作为某类受限
语义声明，必须明确该声明可承担的责任、来源及 assurance 上限，不能将其升级
为 `same_extracted_net` 或完整 body assurance。

### 样张 4：已经提供证据，但绑定错误

输入选择了 `extract-42` 或外部窗口；该证据绑定 `layout-h0`，实际已交
`layout-h1`；或 pin map 的目标是 `TOP/U8`，用户操作对象是 `TOP/U7`。
即使 cell/net 名相同、数值 bbox 相同，也不能视为当前证据。

输出定位到具体 selected evidence、期望/实际布局版本或 instance、受影响关系
与原因，拒绝用它证明 body/父级关联；保留已读取 source bytes、原有诊断及
已独立认证的本地事实。这个请求不能静默退化成“用户没有选择 body 资料”，
更不能选择另一份同名证据自动修复。缺文件、格式错误和已证实不导通/enclosure
违例同样报告真实边界；不得一律改成 unknown。后续分析入口可以显示保留事实，
但不能把整个含错误的请求报告成成功。修正后重新认证受影响闭包，再决定许可。

## 最小资料与操作边界

按需要补充资料，不预设用户必须提交完整父级布局或 toy context 文件。

| 要证明或执行的事项 | 最小资料/前提 | 资料不足时 |
| --- | --- | --- |
| 本地语义与几何分析 | cell source bytes/version/top、CDL profile/model、单位与几何 capability；需要 query 时附同源 run/database/layer mapping | 只运行已有证据能支持的检查，保留实际错误、缺项和覆盖范围 |
| 本地端口的几何 access | profile 下的确切 pin/port region 与 source 绑定、access policy | 只保留端口名和 net membership，不声称已找到 access |
| 父级/global supply 关联 | 具体 instance path、child pin→parent net mapping、global/domain 声明及依赖版本/来源 | 本地 VDD/VSS 等 net 仍已知；父级角色和电压关系未知 |
| 独立物理 body 路径 | 必要 body/tap/rail/边界对象、完整路径 scope、单位/变换、source 绑定、tech/operator/rules 与全部适用对象覆盖 | 不建立外部 edge/assurance；指出所缺路径段或规则 |
| body 冻结下的受限修改 | 可信且匹配当前 baseline 的提取证据、profile 的 body/boundary invariant、明确 affected scope/halo、候选保持证明及其它 mandatory 条件 | 可以生成诊断草稿；不得提交/发布依赖该证明的修改 |
| 完整生产运行 | 所选生产 profile 所要求的完整证据、可信 baseline/当前提取与各项准入条件 | 在缺必需条件的阶段拒绝；不以部分分析成功替代完整运行结果 |

所有证据至少绑定相关 source bytes/content ref、top/cell/instance、对象及 region
版本、run/database、单位和坐标变换、tech/model/deck/profile/operator、来源与
scope。真正必需的闭包随证据路径确定；只比一个任意摘要或同名对象不足以闭合。
变更后按 affected scope 失效和重验，旧 source query 或受信报告不能自动迁移到
新几何。外部 scope 始终独立，不进入本地 occupancy、导出或凭名字创建 union。

## 后续实施与 PM 接收点

建议 PM 后续先安排生产材料调查和生产读取/分析入口任务，再安排选定 profile
的 body/冻结能力与完整运行接入；分别交付缺证据、错误证据、可信替代、人工
标注、超范围修改的失败测试及能力报告。本轮 W014 只实现已授权 synthetic
关系层，本方案不依赖未知生产文件才能交付，也不改变 G1–G4/G5 真实准入门。

当前推荐不要求用户再次选择 D1，也不预先承诺某种生产 JSON。若真实资料表明
必须在几何窗口、受信提取冻结或其它方式之间选择新的关键输入/能力承诺，
执行者应给 PM 最小输入、输出、不能证明的反例和成本影响；由 PM 按协作规则
处理必要的用户决定。仅人工网名标注不证明导通、错误绑定必须拒绝、缺上层信息
保留本地已知事实这些既有边界无需再次决定。
