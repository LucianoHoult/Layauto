# W024 方案

起点为 `11506059006f7fb377732b4d0287e1f4fd72e057`。验收依据是[任务 A1–A5](../W024-stage3-rule-context.md)与[架构 §2.4、§8、§11.7](../../architecture.md)。

1. 在 `pipeline.open_constraint_context(repository, run_id, context_ref)` 校验当前 attempt 为 sealed_open、持有指定 context，沿其 checkpoint、head、snapshot 读取。校验 lineage、target、同次 checkpoint 和内容绑定。使用检查 run 的采集记录、bundle 所选 owner 路径和绑定摘要。复用时 head/snapshot 保留创建者的身份，结果另列本次 run/context/checkpoint/tool。缺引用或跨接以具体引用及原仓库错误拒绝。入口仅读取不可变记录，原候选及输入目录可释放。
2. 由 tech 保存只读 RuleRecord、规则原件定位及整份 mandatory policy。遍历所选 owner 的实际 rows，保留完整声明、顺序、来源 URI/SHA/JSON Pointer。constraints 的执行能力单独匹配规则 ID、evaluator 版本、关系、作用域及所用物理算子。其它已声明规则 pending；可定位的缺项标为 indeterminate。已被 Stage 1/2 拒绝的输入保留原始定位，不伪造已封存的运行。
3. `constraints.check_m1_spacing(context)` 返回绑定本次快照的各规则结果。读 snapshot 精确记录、层声明和 canonical DBU 单位，对所选 M1 全 cell 枚举无序对。使用现有 same_layer_contact 的正面积/正长度共边语义，点接触间距为零。精确比较欧氏距离平方与所选阈值平方，保存每对的 dx、dy、平方、两个 record ID、矩形与 GDS 原记录位置。工艺算子契约不匹配或缺少必需上下文走 indeterminate_then_reject，检查器运行异常单列 error_then_reject。中断继续传播。
4. 用正常、C14 临时副本选择 W022 完整坐标并重绑。验证移走文件后首次打开、复用相容 head、拒绝交叉引用、反查 2480/2544、5 nm 等号与 4 nm 违规、斜向及点/边接触、换阈值/算子或 evaluator 声明、全目录仍可查询。每次查询核对 repository 观测和 sealed_open。示例分别计时首次加载与单次 T07，给 PM 可复跑的文件及输出。
5. 新增合同及受影响 W023 读回/复用、上游规则校验、几何接触和模块方向按身份留证。独立 reviewer 先复核本方案，之后审实现并从原始 GDS 复算；记录发现和处置，再将完整提交推回执行分支。PM 维护验收及集成状态。
