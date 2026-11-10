# W011 合并前独立几何与定位专项

Reviewer：本次新会话 `/root/geometry_review`，2026-11-10；未参与 W011 设计、实现、正式测试编写或既有 review。受审 base 为 `61775e8fde6e9ea247ec08a32067c44c3be48ff8`，head 为 `8452027e57fb1c58607640d7eb755b38ffc70716`。本专项没有修改 runtime、正式测试或固定输入/答案，也没有提交。**本专项新增/剩余必须修正项 0。** 资源与完整 A8 判断交主 reviewer；本结论只覆盖下列范围。

## 依据与静态核对

已读根 AGENTS、README、协作及本地/远端环境规则；目标路径无局部 AGENTS。读取 W011 任务、plan/plan-review、execution/code-review、PM receipt；直接回查 architecture §3.1–3.3、§4.5–4.8、§5.3–5.9、§11.2/11.5/11.9/11.15、§12 的单位/layer/derived 合同，W003 contracts 及 MR-006–009、MR-031/032.1，W004 R1–R5 的原要求，W007–W010 输入/结果接口，以及实际 physical/derived/drawn/formats/rules owner。核对本 head 的 runtime 与 `8917d38d916c914bfa785cb116982f3f299b38de` 无差异，不把 PM 后补文档视为新受测源码。

| 条款 | 独立核对结果 |
| --- | --- |
| A2/A4 身份及 coverage | `locate_channels` 对每 seed 枚举所有 channel 正面积交集，再逐 source device 检查所有 seed，最后检查所有 recognized channel；没有名字、Y、排序或另一个 seed 的消歧 fallback。多份同身份 seed 只增加证据，不产生 finger。`rational_cover` 对交集做 exact union；`full_coverage` 与唯一关联分开。 |
| A2/A3 几何 | `evaluate_fins` 只消费真实 channel/active/FIN record，正面积、完整 channel X 跨越及 active Y 包含决定资格，等号允许。每 channel 保留每 FIN 判定、source、实际 width、原重数及 relation。没有 source NFIN/query bbox/面积除法反填，未写 DeviceIR。 |
| A3 重复/重叠 | 正面积重叠 records 的关系及两来源保留；涉及 channel 正面积候选时 count unknown，不能证明独立物理根数就 typed unsupported。完全不触及 channel 的重复仍保留且不污染其它计量；没有默计双根或 bbox 去重。此保守边界不冻结新的工艺解释。 |
| A5 部分计量 | `_comparisons` 仅对成立的 DeviceId association 比较 source；count unknown 只省略 count 轴，仍保留 L 和全部正面积 crossing 的实际 W。零 crossing 的 W 在 `coverage.unmeasured_width_channels` 明示未测。`differences` 保存全部 mismatch。target 保留在独立 semantic result，不参与几何计量。 |
| A2/A7 拓扑与 scope | `_topology` 从同一 W009 terminal 的有序 S/D regions 找 W010 node/component，并保留 channel 全部 POLY contributors；两个 channel 可共享完整 G。没有建边、union S/D/body、删除 audit 或修改外部 body。NF/M=1 是 admission；不声称几何验证了 NF/M、model/VT、所有端子网络、T02/全部规则、U06、no_change 或发布。 |
| CR-05 关闭 | 最终 `seed_source` 解包 `field_sources.record_id.sources[0]`；message 含真实 record ID，不把其 JSON pointer 覆盖为分析字段。此次新探针重新解析 D0/D1 两原 pointer，结果如下。 |

## 本次实跑

解释器为已有 `/workspace/.venvs/layauto/bin/python`，Python 3.12.14；直接导入本 worktree。没有安装依赖、运行 EDA、读回原安装树或调用完整 W010/W011 Result codec。命令均从 `/workspace/Layauto-w011-review` 运行，exit 0，stderr 为空：

```sh
PYTHONPATH=. /workspace/.venvs/layauto/bin/python -B docs/tasks/W011/independent-premerge-evidence/geometry-probe.py
PYTHONPATH=. /workspace/.venvs/layauto/bin/python -B docs/tasks/W011/independent-premerge-evidence/geometry-location-probe.py
```

两个脚本、最终 stdout/stderr 与 hash 见 [geometry-receipt.json](geometry-receipt.json)。第二个脚本复用第一个脚本的本次独立 setup，不把重复执行的同一检查加成新的独立样本数。脚本迭代均成功，无实际 harness 失败被丢弃；交付的是最终扩展脚本及相应成功输出。

- **实际 normal capture：** W005 acquisition → W008 → W009，同一 GeometryInput 上运行 W007；不使用正式测试 helper、oracle 或 fixture 生成器提供答案。40 drawn records、18 FIN、每 channel 全18判定（共36）；MN0 channel `[58,20,62,70]` 的全部 crossing 为 `[58,y,62,y+2]`，y=24/34/44/54/64；MP0 channel `[58,110,62,180]` 的全部 crossing 对应 y=114/124/134/144/154/164/174。count 为5/7、L=4、全部 qualified W=2，FIN/source 回链逐项相等；实际 W007 两 source devices/两 seed 均唯一关联、coverage=1。这是完整集合检查，不只是两 count。
- **独立 FIN 判据：** 325 个生成 rectangle 对真实 N channel。以 integer unit open-cell 集合与 closed endpoint Cartesian 集合独立判正面积、完整 X 覆盖、active Y 包含及 touch，未调用产品 intersection 作 oracle。结果 13 outside、62 touch、226 partial、24 qualified，逐条状态与 count/unknown 一致。端点枚举覆盖 channel X 和 active Y 的严格内外与边界等号。另实核同一长 FIN 在两个不同 X channel 各有 crossing；同 Y 但无 X 交集不计。
- **独立记录关系：** 两重合 FIN / 两部分重叠 FIN 均保留两 evaluations、relation 和 unknown count；两条位于 channel 外的重复 FIN 保留 relation，count 为已知0。未为重复/重叠根数添加任何新答案。
- **8 个 neutral self-consistent seed 变体：** partial coverage=2/5；有理 X=60.5 的 coverage=5/8；同身份重叠多 seed 的 union=1；缺失 seed；仅触边；一个 seed 同时命中两 channel；两个身份指向一个 channel；同一身份分别指向两个 channel。逐例核完整 seed/candidate 个数、association、coverage/full 标志、明确 issue 及 located source。
- **全部 devices/channels：** 删除 MN0 seed 后 MN0 的缺失和其 channel 的未关联均报告，MP0 关联保留；添加第三 recognized channel 后原两关联保留、第三未关联明确报告，不因 source 只有两器件而丢掉第三 channel。
- **独立 exact union：** 300 例 rational rectangles（分母7/11，偏移0、+10^90、−10^90），62,900 个端点/内部点的 half-open 成员计数对照。验证 union 每处等于原集合、输出无重叠、记录重排及整组重复不改变 canonical cover。正负大数属于本次数学探针，不冒称 GDS32 输入允许此规模。
- **CR-05 独立关闭：** 对合法原 seed 的 neutral 触边变体，两个 `MissingSeedChannel` 分别保留 `query/requests.json#/requests/0/record_ids/0`、`#/requests/1/record_ids/0`，源 SHA `57f5f38cb3ec450fd1815ef88c618c03a9703690672348b313fa35fbce97bc62` 与实际原文件一致，JSON pointer 实际解析分别为 D0/D1，message 亦分别含 D0/D1。

第一次最终扩展 probe 为5.586s、整进程 ru_maxrss 45,972 KiB；location 附加 probe 为3.225s（含重复基础检查）。这些小探针的资源不能代替完整 Result/readback 资源测量。

## 限制与交接

本次数学变体通过公开 neutral DTO 构造保持字段/operand 自洽，明确不是修改后的 captured bytes，也没有声称通过整个 Result 的捕获认证。正常例实际 acquisition 已运行；原 extraction_mismatch 的真实 4 对 source5、target-only/未知count下L/W/零crossing、via_enclosure、readback/无IO及完整公开重建由主 reviewer 的本次定向回归、静态合同检查和按身份采信的历史双矩阵分别承担，不由本小探针冒称新实跑。

几何及定位专项没有发现新的必须修正项。完整 Result 捕获/codec/异常、包/安装矩阵、资源成本与集成可用性的最终结论由主报告给出；不在此自行 PM 验收或批准合 main。
