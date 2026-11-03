# 本轮输入认证专项复核

本专项 reviewer `/root/input_review` 未参与 W008 实现或原 review；只读检查产品，未修改 fixture、答案、原报告或任务记录。受审真实 HEAD 为 `131f66dfadd77b5fb9073db999d6939051c3addf`，审查时 checkout 干净。新增必须修正项 **0**。

## 代码核对

- `normalization/geometry_input.py:47` 的 `capture` 固定 completed 的角色位置和 arity，并要求角色引用指向完整 captured file。`:58`、`:88`–`:120`、`:137`–`:158` 用既有无 IO decoder 重解 site、bundle、六 owner、policy、header、body 与 GDS，随后 canonical 比较 accepted payload；value/completed 同步伪造不能替换 capture。
- `geometry_input.py:73`–`:86`、`:94`、`:103`、`:128`–`:142` 区分首个 acquisition 与后续 alias。已对照 W005 `reader.py` 的 `_Files.read` 缓存与 acquisition 顺序：独占 schema 的初次 selector 必须原样保留；target 复用完全相同的 source capture 是允许的后续 alias。已被捕获的 URI 必须精确匹配选定 role，即使内容/hash相同也不能换角色。未被捕获的后续 alias 保留 W005 路径解析事实，不重新解析文件系统。CR-01 修复符合该边界。
- `geometry_input.py:124`–`:127` 要求 body 恰好两个来源及第二来源精确等于 GDS role；`:149`–`:185` 检查 header/body 来源选择与 GDS/top/unit/profile/operator/scope；IR-01 涉及的跨文档关系均有实际检查。body associations/空间解释有意留在后续，没有当成 W008 缺陷。
- 真实 W006 readback 经既有 `ReadbackBinding` 核对 content ref、run/tool、checkpoint、captured source bytes、completed evidence 的关联；W008 未新增 repository/pipeline 调用。
- `geometry_input.py:62`–`:70`、`:108`–`:111`、`:154`–`:157` 只转换预期 `InputError`，保留 issue 和 completed；`geometry_codec.py` 先 decode children，并对 `GeometryInput` 避开通用 shape-error translation，保证嵌套 unexpected decoder exceptions/中断原对象传播。`GeometryResult` 再把中立 layout 的 GDS/drawn/formats evidence 与 authenticated input 绑定，不能用中立草稿自证成功。

## 本次实跑

`probe.py` 在本轮新建独立环境 Python **3.12.14** 下完成 **24 项通过**，退出 0。精确命令、版本、受审 SHA 与脚本/原始输出 hash 见 `receipt.json`，原始输出为 `output.txt`。

这些判据检查角色关联和结果语义，不以正常 record/fragment 数量作为唯一判据：

1. 真正 W005 读取后的 input/build/canonical wire，全程禁用 Path 文件读取/resolve、builtins.open、subprocess run/Popen 与 repository.read。
2. 保留并运行原 CR-01 reproducer，捕获当前正确的 `GeometryCaptureBindingMismatch`，核对 `site_config.yaml#/inputs/gds` 及全部 9 项 completed；没有把旧脚本最后的旧成功断言当作当前测试要求。
3. 在临时副本令 source/target 两个独立文件具备真正相同 bytes/hash，再交换二者的 derived payload/role refs。W007 semantic receipt 可接受语义相同，W008 按首个 selector 正确拒绝 source 角色交换。
4. 给 GDS 添加 same-byte/hash 的外来 captured role，分别攻击 body 第二来源、header.layout 和 body.source_gds；全部拒绝，保留定位与 completed。
5. 对中间第 20 个 GDS record 的三种 stream/byte positions 同时改 value/completed，保持 captures 不变；全部按 `/gds` 拒绝。
6. 把 same-hash 错 body backlink 埋入成功 `GeometryResult` 的嵌套 semantic-input wire，decode 重新认证并正确拒绝。
7. 在真正 W005/W006 输入中同时使用六 owner、tech bundle、三 policy、GDS/source/header/body 的多组合法 symlink aliases，target 复用先前 source；组件 no-IO 构建、wire 与语义归一化均可完成。直接读取和真实 repository readback 的 layout/occupancy 相等，geometry semantic digest 与正常输入相等，attempt/terminal保持 unsealed/None。
8. 对 `load_document`、`validate_document`、`validate_tech`、`parse_gds` 四个入口，分别注入独立 `ValueError`、`KeyboardInterrupt`、`SystemExit`；嵌套成功 result 的 decode 均传播同一 exception 对象。

## 覆盖限制

本专项聚焦 A1/A2/A6 的输入认证与错误边界；数学占用、完整 v2/typing 和附件身份由本轮其他独立专项/主 reviewer 汇总。这里未复跑 Python3.10/3.11 或重新构建安装包，未验证真实 EDA/PDK、生产准入、跨进程 durability、body/connectivity/annotation 等后续能力。无新增 merge blocker；本结论不代替 PM 验收或 main 集成决定。
