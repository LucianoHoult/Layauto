# W009 执行方案

基线：`4975e565a33d9594782645b6ad0f944b78ee6ae8`；执行集成者 `/root`。只实现任务 A1–A8，PM 要求、阶段及验收不由执行者改写。

## 输入与算子

公开入口 `build_effective_geometry(GeometryResult)` 消费成功的 W008 结果；不读文件或 repository，不重新运行 W007。结果完整保留该 W008 receipt（包括 run readback、全部 parse facts、body 证据及 semantic input）。W008 的 GeometryInput 已重新解析同一次捕获的六个 owner。新增 physical evidence 从 tech record 的 physical source role 构造，成功 aggregate 与输入的 payload/source 逐项比较；不能接受另传配置。neutral state 只检查内部一致性，normalization 成功合同另外检查捕获关联。

在中立领域模块集中列出本轮真正消费的声明：physical.fin_count_profile 的 id、representation、identity_OD、recognized_channel_operator；device_extraction_contract 的 id、sd_policy、gate_operator；operators 中 rectangle_set_difference/1 与 terminal_split/1 的完整语义。检查 drawn 中 cut role 的目标及 operator，目标必须为声明的 LI；明确核验选定 toy profile 的 OD=diffusion、POLY=gate、LI=interconnect、CUT=cut；先查找这四个声明，再检查角色，不能先按 cut role 筛选而静默忽略被改错角色的 CUT。未知/矛盾消费声明定位 source+field 并返回组件 error，保留先前 parse facts；其余 required operators 不宣称实现。保留 W005 schema/unsupported 和 W008 receipt 异常边界。数学几何无法适配时定位 OD 源记录。只捕获专门的预期问题类型，意外异常/中断同对象传播。

## 精确集合、分解与来源

`domain/regions.py` 定义 closed/versioned 的 RegionRef、RegionPieceRef、ExactRegion/RegionPiece 及消费算子绑定。`state/regions.py` 拥有纯集合运算及有效草稿，依赖 domain/tech 中立合同，不依赖 parser/normalization。每个被 CUT 作用的 drawn record 独立保存一个 record result，即使完全删除也有空 regions。贡献 CUT 是正面积命中的原始 records，按 typed identity 排序；重复 CUT 的集合几何只算一次，来源全部保留。重复目标 records 不按 bbox 去重。非消费图形保留为 W008 原始 refs，不制造新 drawn record。

差集实现使用 exact integer x slabs：在目标边界及裁剪后的 CUT x 边界处分段，合并每个 slab 的 CUT y 区间，从目标 y 区间扣除，得到所有正面积区间；跨相邻 slab 合并完全相同的 y spans，最后按 bounds 排序。相邻多余边界不会改变 canonical decomposition，重复/重叠/输入顺序不改变集合。空差集显式保存；孔洞保持为矩形集合，不 bbox 填洞。区域内部按正长度共享边连成分组，角接触不合并；这只是有限矩形集合分区，不建立跨 record 或电气 component。

Rect 的半开形式用于面积/点归属和避免重复计数。region 的闭包边界仍可供后续 contact 谓词读取；正长度边、点接触的电气语义本轮不推导。内部 slabs 不替代 W008 raw partition，更不构造工艺合法网格。W008 base occupancy 原样保留。

Region typed refs 绑定 owner record id、角色、完整贡献记录 refs、单位、消费算子绑定及精确 rectangles；piece refs 绑定 region identity+exact rectangle。聚合 constructor 重新计算完整 expected record/region/piece 集合，拒绝漏片、多片、外来来源、单位、算子、填洞和非法 success。输入遍历重排不改变同一组 records 的结果；真实 GDS record 重排改变 source identities，因此 provenance refs 应改变，另提供忽略 source 排列而保留重复数量的 geometry semantic digest。

## 沟道和端区

每个 OD record 是 identity_OD active。从 POLY 实际矩形中筛选正面积相交；需要唯一 gate stripe。完全相同 POLY 几何按集合 stripe 识别并保留每个来源；不同 POLY 矩形同时命中时拒绝，不能猜测是否为一个 gate。channel 是精确交集，必须横跨 active 全 y 高度且 x 严格在 active 内部，从而余量恰为完整左 S 和右 D。无 gate、多 gate、边角接触、横向/部分高度/全覆盖/贴边导致无法形成左右端区，均定位拒绝。不凭 ON/OP/CDL/query 名称和 record 序号决定 geometry。channel+S+D 内部互斥并还原 active；POLY 保持原样，完全不建立 S↔D edge。S/D 是 toy 空间角色，不是 canonical DeviceId 或 net join。

## API、wire 与验证

normalization/effective.py 提供结果和组合，effective_codec.py 提供 closed/versioned canonical wire，可嵌入既有 geometry codec bytes；只允许明确的 nested types。constructor/decode 都经过 neutral aggregate 和捕获关联检查；tuple/frozen map 复制 alias。error 也须匹配输入当前可复现的问题并保留 completed。success 仅表示本次区域计算完成。

测试包括：独立手算 normal 的 2 channel、4 端区；special GDS 临时重绑并检查 LB 两块与 A_REMOTE；单/多/重叠/重复 CUT、洞、分离、边/角、未命中、全覆盖、负坐标、大整数。独立坐标 arrangement midpoint 逐格 membership 判据配合包含、交叠、面积及边界反例，不调用产品算法生成 oracle。真实 W005/W006 两条链及禁 IO，semantic/query/body/attempt 不变；修改 owner/单位/source/run 的成组伪造，所有 public DTO 和 wire 嵌套反例，alias/mutation、顺序和 hash seed，异常/中断同对象传播。保留原 730 项；Python3.10 与开发解释器、strict mypy、build、两种新包干净安装及源码外真实组合 smoke。

复杂度披露：单目标 m 个命中 CUT，至多 O(m) slabs，每 slab 排序/扫描 O(m log m)，分解输出最多 O(m²)，朴素区域分组 O(p²)（p 为分解片数）；逐 record 求和，可能额外 aggregate 重建常数开销。无新增外部资源上限，记录实际压力规模和时间，不把有限样例当生产保证。legacy 调查：split_diffusion/cut_ops 是 engine cell stamping，状态与近似语义不适用；没有复用其 runtime 或 tests/support 数学逻辑。

## 交付与后续

方案先由未参与设计的 reviewer 独立检查并记录 findings，原范围内修正后实现。代码完成后另由未参与设计/实现者 review；必须修正项经原 reviewer 复核。证据保存源码/测试/配置内容身份、命令/输出、解释器/包来源、性能规模及限制。提交推送当前分支、核对远端完整 SHA 后交 PM，不自行验收/合并/开启后续任务。完整工艺坐标及 region occupancy 投影、contact/connectivity、FIN/body/U06、extraction/overlay、mandatory rules、baseline/terminal 仍按任务后续组合表保留。
