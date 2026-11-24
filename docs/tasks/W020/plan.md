# W020 执行方案

起点 `fd629b1a0afc7b8dedb3ea0da52c86c574a7b210`。输入使用 W003/W004 flat synthetic 文件的临时副本。逐层变体按 W018 从 tech bundle 选择 coordinate owner，同步 query header closure。两个入口的输入语义沿用现有合同。

## 同一捕获的流向

1. `prepare_inputs(repository, request)` 读取 site 及其选择的文件。拟在 pipeline 增加 `assemble_stage2(repository, ready, *, fragment_budget)`。按 ready.run_id 比对仓库中当前 attempt，按其 checkpoint 和有类型的 parse/tool/evidence refs 回读已捕获内容。交给 `geometry_from_inputs_ready` 核定来源。组装阶段无文件 IO 或仓库写入。
2. 同一个 GeometryInput 依次交 W008 → W009。W018 用这一对结果投影 drawn 与 effective。W010 用 W009 和已捕获的规则建物理图，W014 复用此图组装 W007 的 source/target/typed diff、沟道、区域标注和有限的 body 关系。组装只接收单份认证输入，不接受单独传入的图、标注或坐标。组件失败保留原阶段、问题及来源，预算不足保留实际需要量，不返回完整组装。
3. 第一次实取的 LI 原图来自 `source.gds` 偏移 1648；[28,34) × [30,55) DBU。LI 格 (1,3) 的 drawn/effective 片均为 [28,34) × [30,40)，面积 60 DBU²。按同一 record ID、piece/region 与正面积交集查 W010 的 node 和实际 component，再查 W013 对应 target、coverage、`net_shapes_n_lo.txt` 的 toy_li 与 `nXref.temp` 第 11 行的 n_lo→VSS。每一跳输出实际 ID 和输入位置。另检 M1 (2,2) 右端 [32,45) × [48,58)，面积 130、偏移 2352。复核时从 raw 字节独立检查物理或标注来源。
4. A/B 两个同名 cell 的真实文件捕获交错读出。以 coordinate/target/抓取引用及来源区分两者，即使之后原文件改变仍能组装。采用 W003 unsupported_target，保留 MN0 长度 4n→5n 和双方字段位置，核 MN0/MP0 的 FIN 分别维持 5/7。正常与异常返回均查 attempt revision、phase、terminal。只读示例另展示原坐标配置。
5. 示例报告从同批对象取六类事实与来源，仅保存小型定位符与结果。每层分别列原图数、声明、drawn/effective 片和缺项，保留未标注图形、本地及外部 body 范围。用 POLY 的缺声明说明具体阻断。记录完整运行示例、参数、Python、耗时、峰值 RSS 与报告 UTF-8 字节数。交付列事实补齐、逐层初始化、原子发布与后续无修改判定的验收输入。

见[任务卡](../W020-stage2-baseline-readiness.md)与[独立方案复核](plan-review.md)。改动限内部编排、可复跑诊断与定向合同；双版本全量交阶段集成。
