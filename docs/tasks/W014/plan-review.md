# W014 独立方案 review

2026-11-13；reviewer `/root/plan_review` 未参与方案调查、起草或实现。
规则专项 `/root/plan_review/rule_scope_check` 同样只读。只写本报告，不改方案、
runtime、正式测试、fixture、历史证据、PM 要求/阶段或 current-work。

**方案可进入实施，剩余必须修正项 0。** 原 PR-01 与 PR-02 已由执行者补清，
本 reviewer 读取修后原文并对照实际生产者复核关闭。本结论是方案实施门，
不是代码 review、工程验证或 PM 验收。

## 受审身份与独立核查

仓库 `/workspace/Layauto`，分支 `codex/w014-terminal-body-relations`，
HEAD `8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4`。开始核查时仅有 W014
方案/工程准备和 work 中间文件未跟踪，没有产品变更。适用 AGENTS 只有根文件。
受审材料是此 HEAD 上的下列工作区文件；SHA-256 绑定本次门结论：

| 文件 | SHA-256 |
| --- | --- |
| [plan.md](plan.md) | `5d4b634f5071d0fdf43b0359eed6c46b082aea666525ae73ed3881fe097978ca` |
| [body-design-notes.md](body-design-notes.md) | `85b341a5f8b886e3477f9512dabde639ebe7168f3851ff61e4a940020d94cfde` |
| [production-body-scope.md](production-body-scope.md) | `ad311bb6732d1cd1d544f966e3fccd3436aab458919b785d6ae5c24f91789751` |

已读取根 AGENTS、README、协作规则、W014 全部要求及执行 prompt；回查架构
§2.3、3.3/3.6、4.5–4.7、5.6–5.9、11.2/11.5/11.9/11.15 原文和 roadmap U06。
对照真实 `normalization/channel_identity.py`、`derive/channel_identity.py`、
`normalization/net_annotation.py`、`annotation/net_regions.py`、W013 codec、
`state/local_connectivity.py`、reader `_body`/record 调用和 tech schema；核现行
physical/drawn/rules、body context、raw n_lo query、W004 REQ-01/helper 参考及
W011/W013 的独立 review、PM 集成证据范围。未把旧 helper 作为新 runtime 或
独立答案来源；未运行产品重资源链。

另用独立简短整数脚本从真实 context 重算边长和四边 margin：MN0 body/rail
接续为90/10nm，MP0为100/10nm；两 tap 的 body 最小margin均8nm，rail均2nm。
核 raw n_lo 坐标900对应45nm，901精确对应901/20nm；W013 的区域相交/分量
关联不能代替这项精确相等。这里仅核方案样张和实际接口，没有宣称 W014 实测。

## Findings 与关闭复核

### PR-01：body owner 的两来源角色不够明确（必须，已关闭）

原方案措辞是“body 的唯一 owner/source 必须在同一 captured source set”。
实际 reader 使用 `record('body', body, body_file, gds_file)`，EvidenceRecord
包含有序的两个 SourceRef。若误实现成单 source，正常输入会拒绝；若只核第一
来源，GDS backlink 可漏验。关闭要求是明确两来源各自角色、顺序和来源闭合。

执行者已将 plan 改为 sources[0] 是唯一 context 文档 owner，sources[1] 是所绑定
实际 source GDS；两项 URI/hash 同属 captured source set，不能丢失或互换，且
payload 的 source GDS/top/unit/FRAME/真实对象继续认证。本 reviewer 对照 reader
原调用复核，方案缺口关闭；实现及反例仍需代码 review 核验。

### PR-02：外部 BTAP 声明不能沿用 W010 的未执行豁免（必须，已关闭）

最初专项提出“额外 body/body_contact role 层可能被漏审”。本 reviewer 继续
核 `state/local_connectivity.py` 后修正：W010 已拒绝额外 conductive/connector
role 声明，不能把该变体伪称已到 W014。此部分降为实际上游边界的非阻塞提示，
保留调查与更正事实。

进一步的实际缺口是 W010 明确跳过 BTAP_N/P 的外部声明；schema 只核引用
存在等结构，允许把 BTAP_N.electrical_connects 改为 `(BODY_P,M1)`。若新算法
仍执行固定 N 链，会违背已提供声明。关闭要求是 W014 明确验证它实际消费的
BTAP role/purpose、对应类型的 body+M1 连接、正面积唯一 contact_predicate、
T05 enclosure_rule，并对未知声明返回对应 owner 字段的 located unsupported。

修后 plan 的 body 段已逐项规定上述核对、profile.types 闭包和逐字段临时反例，
并把额外 role 的真实 W010 拒绝单列。本 reviewer 对照真实 drawn/schema/W010
豁免复核关闭。无需放宽或新增物理语义，不需要新的用户选择。

## A1–A9 判断与实施核验点

| 范围 | 方案判断及后续必须核验 |
| --- | --- |
| A1 | 单一真实 W010 输入、一次 normalize、既有 W011/W013 neutral builders 避免任意两 Result 拼装；neutral 自洽和 captured 真实性分层。代码 review 仍核完整 source/owner/运行/单位闭合及同值不同来源反例 |
| A2 | device+ordered role target、shared gate 多关系、source/local observed/context observed 分列；不调 S/D、不制造 pin access，unknown/conflict/mismatch 分开 |
| A3 | layer+精确bbox唯一回绑真记录，FRAME与全external scope、全部候选唯一性、正长度边与正面积tap、精确query rail；不依赖作者名或 expected_semantic_rail 产生 observed |
| A4 | 全active、local/external N×P、全部external taps而非只指定链；T04/T05阈值来自同源owner，保留local T05；链事实、enclosure结果、八端比较分列。代码 review 不可只见八端equal就忽略rule violation |
| A5 | 七见证、缺operator/context的实际上游边界、REQ-01 45.05对45与点/边/面积区别均已列；错误证据不降级普通unknown，不伪造sealed或terminal |
| A6 | device×四角色完整集包括缺定位的诊断行；W011 4对5与参数差异、W013 coverage/conflict保留；compact NormalizationFacts直接保留target及全部differences，target不参与source比较 |
| A7 | 先查原始native/closed graph再快照、公开构造重算及canonical全字段比较；一份旧完整W010 Value加compact输出。实际认证/重建次数、wire新增量和三路峰值必须由早测证明，不能仅凭调用图声明资源无放大 |
| A8 | 四类具体样张和最小资料，区分父级关系未知与body物理未证、本地已知事实保留；可信冻结/窗口与人工声明证明边界清楚。设计交付不改变reader必填、不预定生产格式、不重问D1=A |
| A9 | 开发新增/受影响，冻结后双全量/typing/build/双clean安装源码外三路；未参与实现者代码review及修正复核，最后交PM。无自行验收、合main或后续任务 |

资源和公开 wire 是实施后的重点：测量须说明 old W010 认证外部调用与其内部
重建的实际边界，共用输入和重复构建成本均不可省略。正常14/8/6是固定样本
断言，不应写成阻止所有合法临时几何变体的产品硬编码。

## 本次实跑、采信与限制

- 实跑：仓库/branch/HEAD/工作区、适用AGENTS检查，以上文档与实际接口静态核对，
  三份方案hash、context独立边长/margin复算、`git diff --check`。
- 按身份采信：W011/W013 已验收接口及历史矩阵/资源证据只用作生产者合同与
  成本参考，未当成 W014 已验证；未复制完整wire或安装树。
- 未覆盖：W014 runtime尚未实施，全部新DTO/codec/组合/反例/资源和最终工程实跑、
  独立代码review、PM验收与main集成均待后续；真实EDA/生产/完整M1仍在范围外。
- 补跑触发：实现偏离本方案、source/test/config/输入/依赖变化、身份缺口、
  新风险或资源显著放大须核受影响范围；冻结新产品仍完成指定最终矩阵。
  仅换review/PM或文档补记本身不触发重复双全量。
