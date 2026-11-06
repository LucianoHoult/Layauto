# W010 独立方案 review

Reviewer：`/root/plan_review`，2026-11-05。未参与本次方案起草或产品实现；输入/异常合同专项由只读子代理 `/root/plan_review/plan_contract_check` 完成，亦未设计或实现产品。

受审仓库 `/workspace/Layauto`，分支 `codex/w010-local-contact-connectivity`，HEAD `9758a157115cc22d91ce095ac2002209b9f210d3`。开始时 staged/unstaged 为空，未跟踪 `docs/tasks/W010/plan.md` 与工程预检 `work/`；后者不属于受审方案。本报告为 reviewer 唯一写入，不改方案、产品、任务或 current-work。

受审[方案](plan.md)完整 SHA-256：`e6578dd652aafab1de41c4a0adf321c2008adcb3ec47585d5bf5f8c7108b0e8d`。

**结论：必须修正项0，方案可以在既定 W010 synthetic/toy 范围内进入实现。** 这是产品方案的独立静态审查，不能替代后续代码 review、A1–A8 实际验证或 PM 验收。

## 核对结果

| 范围 | 独立判断及依据 |
| --- | --- |
| 同源认证及保留链 | 现有 `effective_codec` 往返会重建 W009 draft、W008 base/GeometryInput、NormalizationInput 及 direct/readback 捕获链；`GeometryInput._verify` 从捕获 bytes 重解码所有 owner。方案先检查原始保留图 exact types，再完整往返比较，可避免编码复制掩盖可变别名或仅编码未重新认证的成组伪造。完整原 input/completed/attempt 保留、不读文件或 repository 的边界正确。 |
| rules source role | 实际 `geometry_input._OWNERS` 为 drawn/derived/physical/formats/coordinate/rules，tech evidence 第6项确为 rules 完整捕获 source role。payload 实际路径为 `effective.input.input.value['tech']['rules']`；方案的链路简写应按该已有结构落实，不建立第二份 rules 权威。 |
| 独立 region 计数 | OD S/D、LI 的每个独立 ExactRegion 与每条 POLY/M1/BODY 原 record 各为节点，channel/connector/外部 context 不作本地导体。逐 connector、逐声明侧在 component 合并和 enclosure 检查前做 positive-area region 计数，能拒绝重复导体或同层已相连的两个候选，保留重复 connector 各自来源与 audit。符合实际 physical/drawn 声明。 |
| 精确接触和完整图 | 穷举有限节点对避免 raw occupancy 原轴漏掉 CUT/channel 新边界。piece 交叠或正长度共边成一条 region-pair 边，点/角不成边；全部节点初始化 BFS 保留孤立节点。中立 aggregate 重新生成完整 nodes/edges/audits/components 后比较，足以作为漏边、多边、伪造 union、丢孤立节点等公开 constructor/decode 的验证基础，叶 DTO 的结构检查不能单独宣称完整性。 |
| enclosure 与图成功分离 | 图 `success` 可以伴 `local_enclosure_status=violation`，edge 不因 T05 violation 消失。该局部状态不代表整个 T05、mandatory 或运行准入通过，符合 VN 仍唯一接触两侧而 LN 包围不足的既有反例。Fraction 扩张加 exact x-slab/y-interval 无缝覆盖可表达跨pieces整体包围和孔洞，允许边界等号，不依赖 bbox/单片或面积相等。 |
| refs、语义及范围 | binding 的 effective ref、完整 owner、单位、top/local scope 与来源几何链进入 typed refs，component 绑定完整成员。另以几何/拓扑多重集合形成 semantic_digest，区别来源身份和重排不变语义。没有按 net/device 标签加边、S↔D union、外部 body union 或跨 mutation lineage 承诺。 |
| 异常合同 | 相关既有 nested codec 对 Input/Readback constructor 没有宽泛 TypeError/KeyError/ValueError 翻译。方案只捕获显式 ContactProblem，schema 预期错误与算法故障分开，nested codec 直接委派，符合原对象及 cause/context/suppression 保留要求。需要按已列矩阵实际验证，不能从静态委派推断通过。 |
| 验证与交接 | A1–A8方案覆盖真实 direct/readback、正常成员而非仅数量、cut-islands、via_enclosure、重复与歧义、公开 constructor/wire/alias、完整 nested 异常链和原1149项能力，双解释器/typing/新包/双干净安装源码外 smoke。完整快照、环境、命令输出和包/安装身份的交付要求明确。未扩展 U06、body、grid、提取、发布或真实生产能力。 |

## 实现时的核验重点

以下都是方案已承诺的落实检查，不是新增必须修改项：

- 完整类型白名单必须覆盖 effective、geometry、semantic、publication 的实际保留 DTO；原对象图检查发生在任何复制/编码之前。
- normal result 的成功图与局部 audit 状态各自验证；不能把 violation 写成无 issues 的全部规则通过。
- 实际资源记录须同时计入完整捕获往返、aggregate 再建图、ref/digest 计算和 wire/输入复制。方案已经披露重复认证；不能只用核心扫描的 O(N²) 表述整条公开路径性能。压力规模和生产未验证范围如实报告。
- 实现后的 malformed wire 对照与算法故障探针分别运行，避免宽泛异常捕获使两者都变成“明确拒绝”而丢失原异常链。

## 方法与限制

读取 AGENTS/README、协作及环境规则、W010要求/方案，回查任务引用中有关 exact输入、Stage2所有权、局部物理图、VIA/CUT/channel、annotation、规则relation、模块依赖与单位的架构原文；核对实际 physical/drawn/rules、正常 oracle、W009/effective codec、W008 geometry codec/input、NormalizationInput/ReadbackBinding及中立region/unit/record合同。输入链专项独立核对完整 roundtrip 和 rules role。仅静态 review 与方案 SHA-256 计算；没有运行 W010 产品测试、typing、build、安装或性能检查，产品此时尚未实现。后续代码改变须由未承担实现者绑定最终版本独立审查。
