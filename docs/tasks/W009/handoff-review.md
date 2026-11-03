# W009 独立派发审阅

- 日期：2026-11-03；reviewer：独立 agent `/root/w009_handoff_review`。
- 审阅对象：`/workspace/Layauto/docs/tasks/W009-effective-geometry-terminals.md`，未提交的派发草稿。
- 分支：`codex/w009-effective-geometry-terminals`；基线：`4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。
- 草稿 SHA-256：`858f3a6e06350e36dd1760cc37cf2a0d7ef890301d7178ce6380c6a4f54d15b7`。
- 结论：**必须修正项 0；可以在该范围内派发独立执行。** 这是要求、接口和范围审阅，不是实现方案、代码或产品验收。

## 判断依据

1. 任务只把现有 toy 声明中的精确 CUT 差集、OD/POLY 沟道和 OD 减沟道后的 S/D 区域做成不可变且有来源的中间产物。实际 `physical.json` 已声明相应 operator/version、每个 active 恰有一个 gate stripe、左 S/右 D 的规则；没有静默增加用户输入或生产格式解释。`coordinate.json` 仍是 example-only 且 incomplete，草稿没有把本轮提升为完整工艺坐标或运行成功。
2. 差集要求保留全部正面积结果，显式表示全覆盖后的空结果，覆盖重叠/重复 CUT、孔洞、多块、边角相接和顺序独立。端区要求完整解释 OD 减 channel 的余量，不能只挑出左右两块而丢失剩余；不能得到已声明的两个有序端区时拒绝。与架构的精确几何和 W003 独立答案相容。
3. 任务将单个区域内部的几何分组与跨对象电气图明确分开，没有提前宣称同层导通、connector、ComponentId、器件抽取、fin 数、body 完备或 mandatory/lifecycle 闭合。正常答案的四个端区和 cut-islands 的 LB 两块、面积 72 及 A_REMOTE 只用作几何期望；其网/连通分量/间距结论不被挪作本轮成功承诺。
4. 输入必须经既有 W005/W006/W008 认证和来源绑定，不能由 query/CDL 名字造几何；失败保留 typed 定位及已完成事实，unexpected failure/interrupt 不伪装成功。闭合 DTO、恢复校验、原始记录多重性、单位/operator 来源和规范身份均列入验收。raw layout/base occupancy 必须保留，有效 region 的 occupancy 投影保留为后续义务。
5. 验收包含独立集合/点归属见证、反例、资源增长解释、既有 730 项回归及 typing/build/安装检查。没有新增未经确认的生产资源上限。U06 作为后续生产输入/body 能力义务保留，本轮不把 toy body 必填推广到生产，也不私增缺失 body 的可选入口。

## 非阻塞建议

- 明写 W008 `BasePartition` 的轴仅来自对应层的 drawn 记录边界；LI 轴不保证含 CUT 边界，OD 轴也不保证含 POLY/channel 边界。因此不能按整格扣除或用现有格子直接代替有效 region。现有“保留 raw occupancy、有效 region 投影后置”已约束正确范围，此句用于减少执行误读。
- 内部方案应明确精确集合/边界表示与 W008 半开索引、后续接触语义的关系，并遵守 A3 已要求的点归属及边角见证。面积相等不能单独证明几何相等。

## 审阅方法与限制

只读核对任务、架构（特别是有效几何/连通/端区范围）、W003 合同与 manual-review 相关要求、实际 tech `drawn/physical/coordinate` 声明、正常与 cut-islands 独立答案、W008 `normalization/geometry.py`、`normalization/geometry_input.py`、`state/coordinate.py`、`state/occupancy.py` 及 roadmap U06。核对了分支/基线和草稿文件 SHA-256。

未运行测试、生成器或 EDA，未核验新实现性能，未修改仓库文件或提交。本文为唯一写入的外部审阅记录。执行者完成内部方案和实现后仍需独立方案 review、代码 review、实跑证据及 PM 验收；本审阅不替代这些门槛。

## 最终派发文本局部复核（2026-11-03）

PM 将以上原审阅记录原样入库后，reviewer 仅核对任务新增的逐层轴/CUT/channel 边界说明、集合与半开索引/接触判据说明，以及“可执行”和 PM 派发记录。两项建议均已准确采纳，阶段明确仍须独立方案及代码 review，未宣称产品验收；**局部复核必须修正项 0，原派发结论保持**。最终任务全文 SHA-256 为 `8df849a6358ae554aea7e09f0a72b033f4d41acb8bd45c38172a36d7826c6593`，路径为 `docs/tasks/W009-effective-geometry-terminals.md`；该身份对应将由 Git 保存的完整最终受审文本。本次未重跑测试或扩展产品审阅，仅向本报告追加本段，历史审阅记录保留。
