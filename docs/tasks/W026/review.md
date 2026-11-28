# W026 独立复核

## A1 实施前复核

审阅基线为 `f8c06e75917e4fa111b63af179d8b5265218fcbd`。审阅人未参与产品或测试实现。依据为本版任务卡、架构 §2.4 和 §2.6、tech/rules.json 的逐项声明和 mandatory_rule_policy、physical.json、drawn.json、W022 完整坐标、W023 发布及 W024/W025 开放与检查路径。逐条方案见 [plan.md](plan.md)。

- 直接用 W022 独立 GDS 流解码器按 BOUNDARY 偏移读取了 40 条原图。唯一外框 @112 为 (0,0)–(160,200)，本地 body 和 M1 轨含边界等号。排序后的 18 条 FIN 下边为 24 至 194 nm、步进 10 nm、宽 2 nm；轨号 [0,17] 来自 W022 选定坐标。检查起止缺轨需要用声明的有限范围。
- OD @304、@368 分别为 Y=[20,70]、[110,180]，POLY @432 的 X=[58,62]，完整跨过两块 OD。分别有 5 和 7 条完整 FIN，两张 CDL 对应 L=4n、W=2n、NF=M=1。定向反例须能发现 FIN 数正确而其他参数错误。
- 从外部 JSON 分别读到 BN.ext/BP.ext、MN.ext/MP.ext、TN.ext/TP.ext，关联目标分别为 VSS/VDD；本地体区与异型体区间距 10 nm。T04、T08 各需检查关联目标和源，T05 两侧几何证据须独立于语义关系。
- 本地 @2096 正常 X=[29,33]，@1648 LI 的 X=[28,34]，上下两边余量 20/1，最小 1 nm。右移后 X=[33,37]，仍有 1 nm 正面积横向重叠，右余量为 −3 nm。TN.ext、MN.ext 原 Y=[50,54]、[48,58]，最小余量 2 nm；前者下移 1 或 2 nm 得 1 或 0 nm。非矩形区域需检查充边后的集合包含。
- 独立比较三个 GDS 的所有流记录。C14 唯一变化在 @2544，左边 80→79，对 @2480 的右边 75 得 4 nm；via 样本唯一变化在 @2096。两变更可分别应用后重绑输入。T06 应另用已有 CUT 缩距样本，从有效区域追至 CUT 来源。
- T09 必须比较不同来源的事实，使用受检运行绑定的原始 GDS、CDL、已发布状态与有序 ECO 链，保留复用 head 时的两条 checkpoint 引用。实际导出文件归 Stage 6。T10 保留每项含未知项的来源、披露策略和物理分量。
- 已与实施方确认逐项保留独立结果、缺资料与执行异常的策略、只读查询前后的一致性以及旧专项入口的选择集。移动过孔或改变 CUT 的旧、新几何范围可影响几何、连通、保真和覆盖，已落实到方案；本阶段仅检查选定版。

方案复核结论为可实施。代码复核将以实际发布和有来源的返回结果确认上述约束。

## A5 整包代码复核

独立检视了 Stage 2 事实绑定和冻结、打开上下文、规则分派、各类算子、证据行、异常与原入口、实际文件示例及合同测试。以下发现、处置及复验由 reviewer 记录。

| 编号 | 初审发现 | 处置和独立复验 |
| --- | --- | --- |
| IR1 | T03 仅对名字和数值轴。将目标 MN0 从 TOY_N 改为 TOY_P，不改 FIN、L/W、NF/M 或端序，数值比较无法识别器件不符。 | 实现增加 source/target model 和双方 CDL token 位置。修后公开结果的唯一 T03 违例定位 MN0 的 model。 |
| IR2 | T10 分组使用不可哈希的 FrozenMap 作 net 键；在正常带标注的数据上即会得到 PredicateExecutionError。 | 改用类型化 net 的规范内容摘要保留身份；同一快照用修订代码求值为 pass。专门的两片同名 LI 合同另外比较原图及各自的物理分量。 |
| IR3 | T03 读取目标方缺少的 selected_cell；在实际已发布输入上返回 InvalidSnapshotOperand，来源为 /channels。源语义草稿和分立 TargetCircuit 的字段不同。 | 以当前已选 cell 标识查 target cells，在对应关系缺失时报告 cardinality。对同一已发布输入重验，几何与模型对照可到达。 |
| IR4 | T10 实施表与注释将标注生产者指向 W012。 | 改为 W013 的几何标注叠加与分量证据。 |

复核时在 C14 的输入上替换来自 via_enclosure 的 VN 单元素，再仅改目标 CDL 模型并重绑。用 W022 流解码器直接核对 GDS @2096/@1648 的四边 (5,20,−3,1) nm、仍有 1 nm 横向重叠，以及 @2480/@2544 的 4 nm 间距。通过公开的 prepare/publish/open/check 路径核对 T03、T05、T07 三项独立原因及七条通过记录。T09 的原始 source 语义、几何和有序 ECO 链均保持，目标 CDL 差异归 T03。检查前后快照、head 和 attempt 均相等。该反例补充交付中的二违规样本，独立脚本见 [review_probe.py](review_probe.py)。

对 T05 四例另实跑了基线自带的 [pm_inputs.py](pm_inputs.py)，正常/右移/外部等号三例的 (本地、外部) 最小余量依次为 (1,2)、(−3,2)、(1,1) nm。第四例在 terminal_relations 返回 BodyTapEnclosureFailure，指向 body/context.json#/shapes/4，未产生 head。多块反例审阅了修改后的真实 GDS 和独立 arrangement_enclosure 判据：1 nm CUT 位于 VN 内部，外框包含充边后的矩形，实际集合在 CUT 处缺一块，独立物理节点与边仍可追溯。

复验命令在仓库根目录执行，解释器为 Python 3.12.14。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm_inputs.py
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/review_probe.py
```

此次独立复核未重复双解释器全量。[交付记录](handoff.md)列有本次范围、对应版本和复跑条件。

被审范围从派发基线到产品、示例和测试提交 `bb998483de34076b20bab48ddbde89e4bae9c85f`。已核对该提交包含上述产品修正并用其算子重查同一经公开入口取得的三项组合快照。任务复核记录单独随交付文档提交。

公开入口复跑退出码为 0，输出为 `T03 MN0 target model TOY_P; T05 VN/LI (5, 20, -3, 1) nm; T07 M1 4 nm; other seven pass; sealed version 0`。探针 SHA-256 为 `a7d7286c78c421e472b5a4c6c0d8adbac185b6c1e5c35dd7ac8124a3090096d8`。初审所列问题均已修正，本范围独立代码复核通过，交 PM 验收。

### T10 来源补充复核

在上述产品提交上另审两文件增量。coverage.py（SHA-256 `3af2877c46fbb775f1305116872f95bad2c1042e910f6c667d89b396c567b96a`）为标注片段补齐 record_id、bbox_nm、schematic_name 的去重来源。test_w026_drawn.py（`984d8de4fc4512fd73b5eb9a5f83a8ad6c9bbb10a362df6e51bbd2ad21b77c17`）在 W013 原始 NET SHAPES 对照变化前删除旧的可选测试缓存，照原路径更新请求及 header 并重绑；另两处断言新增失败诊断信息。

复用上述实际发布并读回的版本 0 上下文，重新显式调用 check_rules。十条独立结论仍为 T03、T05、T07 违规，其余七条通过。对所有 8 个带标签片段逐个从冻结的 evidence record 提取三项字段的来源，核对返回值完整、去重并且摘要属于受检输入。共核对 53 个独立位置，涉及原始 net_shapes、nXref、查询请求与 dialect。该增量独立复核通过。
