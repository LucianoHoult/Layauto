# W009 补修 PM 代码专项核验

日期：2026-11-04。角色：PM 委派的只读代码/边界检查；不是原实现者，也不替代原独立修后 reviewer 或 PM 最终验收。

核验对象：`6cb4ecc2ecaa8bd6e5236b28b70149d9a4917534`；补修基准 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`，最终产品/正式测试为 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9`。本次核对基准到交付的完整 11 文件产品/正式测试 diff：8 个 runtime 和 3 份新增正式测试。读取根规范、W009 原要求、补修交接、执行及独立复核记录，核对架构 Stage1/2 与 domain/state/importer 边界。

**结论：本次专项未发现必须修正项，支持 IPMR-01/FXR-01 的修后关闭判断。** 未修改仓库、运行完整回归/99项矩阵、提交或合并。完整矩阵与工程证据由主 PM 分别实核/采信。

## 实际代码判断

- `geometry_codec` 不再按异常类型包装 layout/partition/occupancy constructor 的内部故障；消费位置对 BOUNDARY 字段集、未知层及 XY pair 等作明确拒绝，聚合事实重建和 canonical 回编比较仍保留。
- `NormalizationInput` 去除请求选择/parse 验证外层 broad catch；`_validation` 的主要改动是缺字段前置检查的 typed lookup，另补字符串 UTF-8、容器/引用/索引和空白 count-header 检查。原来源 hash、捕获字节、lexeme/位置、请求与响应、CDL/模型及 query 覆盖比较仍存在，没有发现用放宽认证来规避原异常合同。
- semantic decoder 仅新增对可达 `ReadbackBinding` 的原异常传播；publication decoder 仅对列明的15种捕获/readback DTO解除 constructor 包装。子 wire 在父 constructor 前解码，未对无关 terminal/failure 代码作机械重写。
- FXR-01 四类公有集合入口现先 shape 检查、只取一次 tuple 快照，再验证并保存该快照；支持原 tuple/list 子类范围，不再验证与保存不同迭代内容。
- wire schema、effective geometry/coordinate/occupancy 数学、闭合原对象图、fixture/答案、架构及 legacy 未变。源码修改与具体可达反例相符；没有新增生产输入解释或放弃既有捕获认证的证据。原完整合法 wire 的跨版本相同结论仍归原独立兼容审计，本专项只实跑当前版本的真实 roundtrip。

## 本次独立有界实跑

自行编写 `probe.py`，不引入 tests/support 或正式测试 helper：

1. 两种有副作用容器（list 子类、额外的 tuple 子类）×四个集合入口×valid-first/invalid-first，共16例。8例正确保存独立快照，8例明确 ValueError；各只迭代一次，list 后续变更不影响保存结果。
2. 真实读取正常 fixture，构造 W005→W008→W009，完整 result wire 解码再编码逐字节相同，1例通过。
3. 仅替换 `domain.evidence` 的 hashlib 模块绑定，分别经公有 SourceFile wire 和完整 W009 result wire 注入9类异常/中断，共18例；原异常对象、既有 cause/context 及显式 suppression=False 均保留。
4. 经正确 scalar wire tag 向 SourceFile uri/data 分别提供 None、整数及错误文本/空值，共6例，均明确 ValueError，未观察到裸 TypeError/AttributeError 或伪造成功。

合计 **41例通过**，进程 exit0，stderr为空。实际环境 Linux/Python3.12.14，使用既有 PM venv，不作为干净安装或双解释器证据。完整输出 `probe.stdout.json` 保存 HEAD、Python/平台、script SHA 及11个受影响产品/测试文件 SHA；`probe.stderr.txt` 保存原 stderr。

复验命令（仓库根目录；脚本放在当前临时路径）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/Layauto /workspace/work/w005-pm-check-env/bin/python -B /workspace/work/w009-fix-pm/code/probe.py > /workspace/work/w009-fix-pm/code/probe.stdout.json 2> /workspace/work/w009-fix-pm/code/probe.stderr.txt
```

本专项没有重跑全部畸形值、原99项矩阵、完整 unit/contracts、typing、包构建、安装、性能或 EDA。有限动态见证不能证明任意运行时篡改、全输入域或生产能力；共享历史 constructor 的未变分支不据此得到额外保证。物理连通、FIN/body、完整工艺坐标及发布义务继续依原 W009/U06范围后置。
