# W009 执行交接

执行集成者 `/root`；仓库 `LucianoHoult/Layauto`；分支 `codex/w009-effective-geometry-terminals`；接手起点 `4975e565a33d9594782645b6ad0f944b78ee6ae8`。本报告由执行者维护，PM 验收段及 current-work 未改写。

## 恢复、方案与实现

云端初始 checkout 是干净的 `work@4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。首次 Git 默认沙箱网络不能连接环境代理；在支持的附加网络权限下正常 fetch，未更换或绕过代理。随后创建指定分支并核对 HEAD 精确为用户指定的起点，staged/unstaged/untracked 均为空。读取了根 AGENTS、README、协作/本地及远端环境规则、current-work、W009 完整要求与 prompt、引用的架构原文、W003/MR 合同及 W007/W008 的输入、身份、单位和公开结果。仓库无后代 AGENTS。

[执行方案](plan.md)先由未参与设计的 `/root/plan_review` 独立审查。[方案报告](plan-review.md)的 IR-01 更正 POLY 的实际角色为 gate，并要求先定位 OD/POLY/LI/CUT 后逐项校验角色，不能筛选漏掉错误 CUT；原范围内修正后独立关闭。没有新增输入解释、生产 profile 或必需用户决定。

新增中立 `domain/regions.py` 和纯 `state/regions.py`：精确整数 slab 差集、规范矩形集合、单 record 内区域分组、唯一正面积 gate stripe、完整 channel/左 S/右 D；typed region/piece refs 绑定来源、单位、消费算子及 exact geometry。`normalization/effective.py` 的 `build_effective_geometry` 消费完整成功 W008 receipt；成功结果绑定同次捕获中的 physical owner。`effective_codec.py` 提供 closed/versioned canonical wire、digest 与嵌套捕获认证。新增公开导出、strict typing 路径、README 及 W007 边界测试的精确纯组件白名单。

中立 region DTO 检查排序、内部互斥、规范分解及单区域连通；RecordRegions 检查 owner/贡献来源/unit/operator 与角色关联。完整 EffectiveDraft constructor 根据 base 和 owner 重建全部结果，拒绝漏片/多片/填洞/外来区域；公开 success 再核验该草稿与完整 W008 receipt、physical payload/source 的关联。单独中立 DTO 不能证明捕获真实性；OperatorBinding 保存未消费字段，但完整 owner grammar 校验由 state aggregate 执行，捕获认证由 normalization 执行。domain 不依赖 tech/parser/state。

CUT 结果逐 LI 原 record 保存，完全扣除保留明确空结果；重复目标不去重，重复/重叠 CUT 只按集合减一次且保留每个命中来源。不同 POLY 几何同时命中 active 时拒绝；完全重合的 stripe 只形成一个集合沟道并保留全部来源。所有 active 余量必须形成 profile 规定的完整左右端区；不支持的几何以源 GDS record 位置和 field 定位。

独立代码 review 发现 CR-01：codec 对 neutral constructor 的 TypeError/KeyError 等异常翻译会破坏内部算法异常的对象身份。已移除该翻译，改由字段结构/中立 constructor 明确检查畸形输入，新增草稿/嵌套结果 16 个算法异常 identity 反例。finding 原文及独立复核归 [代码 review](code-review.md)，执行者不代写 reviewer 结论。

后续独立构造器审查发现 CR-02：仅值比较的 literal/version 字段可接受带可写属性的 str 子类或伪等值对象。已给所有新增 literal/version/unit-ref kind 增加 exact-str 守卫；中立 binding 对完整 evidence 值闭合校验，state 对完整 W008 base 链作 canonical 校验，公开入口对完整原 receipt 验证可 canonical 编码，外层 completed/issues 也作 closed-value 校验。不改变旧 W008 DTO 的定义或重新读盘。随后对原生容器采用先复制后校验，并逐层检查保留的旧 base DTO 集合；完整原对象图在任何 to_value/codec 折叠前检查，只接受原生 Value 原子（Fraction 的分子/分母也必须原生 int）、原生 tuple/FrozenMap，以及固定 allow-list 中的 exact DTO 类。67 个新增反例覆盖 literal、容器多次遍历、旧 receipt/base/owner 子值、编码前类型及 Fraction 内部别名。修前 847 项及中止运行仅保留历史身份；最终矩阵、包和安装按修后源码重跑。

## A1–A8 对照

| 要求 | 实现与可重建判据 |
| --- | --- |
| A1 | 实际 W005→W008→W009 与 W006 caller-read checkpoint/parse/tool/audits→W008→W009 得到相同草稿；禁用文件/repository IO；semantic/query/body/attempt/terminal 保持。成组 physical payload 伪造同时测试直接认证和 W009 嵌套 wire。W008/W007 既有 wrong-run/source/owner 反例随全量回归保留。 |
| A2 | 实际临时 owner 字节修改并重绑 header，逐项反例覆盖消费 profile/算子语义、4 个角色、CUT target/op；W005 缺项/未知算子错误边界保留。未消费 contact 文本不会被宣称已执行。完整 physical/drawn/formats 来源及单位关联保留。 |
| A3 | 单/多/重复/重叠 CUT、孔洞、横/竖分离、角边接触、未命中/全覆盖、负坐标及 2**80 大整数；独立 arrangement 中点/边界线/顶点 membership、包含、互斥及手算面积检查，无 product helper 生成 oracle。 |
| A4 | 正常 2 channel、4 OD 端区均有独立手写 bounds；单 OD 隔离验证无 gate、多 gate、边/角触、部分高度、横向、贴边/全覆盖拒绝及具体 code。第三 active、重复 OD/同几何 POLY 不靠正常数量/展示名称推断。 |
| A5 | 从原 special GDS 经临时 header/body/query top 重绑构建，LB 两块为 [130,20,139,24]、[141,20,150,24]，面积合计 72；A_REMOTE 为 [50,20,60,24]。只证明几何，不声称 component/spacing/T06/T08/T10。 |
| A6 | 公共 DTO 的 list alias/递归 mutation、遗漏/重复/额外/外来来源/单位/算子、孔洞 bbox 填充及非法 success；closed nested wire、canonical roundtrip/digest、三个 hash seed；builder/captured decoder/neutral aggregate decoder 的意外异常及中断按同对象传播。 |
| A7 | raw layout/base partition/occupancy 全部通过原 receipt 保留，FIN/body/marker/未消费图形未删改；S/D 仅 toy 空间角色。没有 ComponentId/net stamp/物理 edge、body/FIN 完整证明、overlay、发布或 terminal。后续接口见下节。 |
| A8 | 最终源码身份、双 Python 完整矩阵/strict typing、新 wheel/sdist、两套全新安装及源码外真实组合 smoke，由 [验证回执](verification/receipt.json)、[源码清单](verification/source-manifest.json)及原始日志逐项记录；仅最终 manifest 身份对应的结果作为交付证据。 |

新增测试位于 `tests/contracts/test_w009_effective.py`、`test_w009_contracts.py` 和 test-only `w009_cases.py`。helper 只编辑临时输入并重绑捕获；没有修改 fixture、答案、历史报告或 tests/support。集合正确性同时检查内部点、边界和顶点，不单靠面积；孔洞 constructor 反例中的错误片集合本身仍为合法 canonical/connected region，真正由父 aggregate 拒绝填洞/漏片/外加区域。

## 资源与边界

单 LI record 有 m 个命中 CUT 时，裁剪、按 x slab 扫描并排序 y 区间的通用上界为 O(m² log m)，输出分解 p 最坏可为 O(m²)；分组朴素 pairwise 邻接为 O(p²)。ExactRegion 另有 overlap 与连通自检 O(p²)，以及 canonical_cover 自校验的一般 O(p² log p) 上界。全草稿逐 record 求和；build 与公开 aggregate constructor 均做重建，有重复计算常数开销，wire decode 还会验证完整 W008 base/captures。CR-02 后新增入口的完整 receipt canonical 编码检查及 state 的完整 base 值链检查，另有与原捕获/序列化大小有关的遍历成本；没有重新解析或读盘。不能仅以 slab 扫描成本代表整条链。

实际规模/片段数/时间、解释器及源码身份见 [performance.json](verification/performance.json)，可用 [performance.py](verification/performance.py) 重跑。有限 toy/压力样例不构成生产性能保证；没有新增外部 geometry 数量限制。W005 原始 1000 stream record 等读取资源合同保持。legacy 调查的 `split_diffusion/cut_ops` 是 engine cell stamping，没有可直接作为本轮精确差集的纯 runtime 代码；未引入 archive/tests-support 运行依赖。

内部矩形分解只为 exact Boolean 运算服务。半开点归属用于索引/计数，闭包边界留给后续 contact 谓词；正面积、正长度边和点触的物理导通解释不由本组件产生。W008 raw axes 未被扩充或删除；本轮没有把内部边界变成工艺合法坐标或 grid 默认值。

后续仍需：完整坐标/合法空间及 region→occupancy/annotation exact projection；same-layer/qualified connector/contact、component identity/lineage；FIN qualification、canonical device/net join、D/G/S/B extraction、spatial overlay/coverage/conflict；body D1=A 物理证明及生产 U06 缺外部 tapcell/全局 power rail 的最小上下文与缺项分级；mandatory rules/lifecycle、完整 ProposedInitialState、baseline/seal/no_change/Stage6 和真实 G1–G5。当前 synthetic body_context 必填保持，未将其泛化为生产需求。

## 验证身份与交 PM

验证使用 Linux Python 3.12.14 和独立 Python 3.10.22；环境/命令/包与安装来源以 verification 回执为准。首次中间回归因扫描新增模块触发旧 W007 边界白名单，随后按授权增加了精确纯 state import 例外；两套中间进程曾被主动停止，未冒记为 730 全通过。CR-02 修前的随后一次 3.12 完整 847 项与 3.10 已运行 821 项也按各自源码身份保存到 pre-cr02，后者收到主动中止；容器/深层值复核前的一次候选验证另保存在 pre-container（3.12 已运行 651 项、3.10 已运行 532 项均主动中止，其当时包/安装 smoke 仍保留对应版本），均不作为修后最终矩阵或包结论。原起点 clean snapshot 的该边界项在两解释器均通过；最终完整矩阵另跑并绑定最终源码。

最终 Python 3.12.14 与 3.10.22 各 **914 passed**（保留原 730 项 + 新增 184 项），双 strict mypy 各 **44 source files**、双开发环境与双安装环境的 pip check 全通过；新 wheel/sdist、两套全新安装和 checkout 外 `-I -B` 真实组合/codec/实际错误 smoke 均通过。15 项实际命令及原始输出绑定最终源码清单 SHA-256 `32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`，完整 240 项快照 SHA-256 `5ed2228559ea6dcf7a1417e19b8f706f1e88283edfca0c01809489cb147ec727`；两个包和两个实际安装目录各 90 个 runtime 文件均逐字节等于受测源码。wheel SHA-256 `27e97b27f8e3a4f5e2ff804a32fe3bd3aa33d3a6ea1f3e9b96075ea5858aaf95`，sdist `2716df4fe382dfb64127ed9b46ee3c80aa53b071bab10175d7e4b65806c72c98`。详见 [最终回执](verification/receipt.json)、[包身份](verification/package-identity.json)、[安装身份](verification/installation-identity.json)。

最终提交推送 SHA 在 Git 和执行回复中记录。提交沿用 `LucianoHoult@users.noreply.github.com`。PM 应核验最终源码/证据/reviewer 版本、已关闭 findings 及后续义务，再决定验收和集成；执行者不自行验收、不合 main、不删分支、不启动下一任务。

源码及交接补丁的空白检查通过；两份中间 baseline 原始 traceback 的 `E` 空行含 pytest 原始尾空格，保留原始字节及日志 hash，未为消除空白提示而改写证据。
