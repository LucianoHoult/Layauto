# INV_M1_SYNTH — no_change 预期报告

**预期样张，未执行产品 run。** 下述 pass/feasible/terminal 是后续 M1 应观察的结果，不是本轮生成器、独立 reader 或真实工具的运行结果。来源为 synthetic，生产接收状态为 `requires_review`。

输入为 source GDS、source/target CDL、四种 raw query 及其 header/normalized、toy tech 与 site policy。完整输入定位和实际样本 bytes hashes 在 [机器报告](report.expected.json)，core 样本文件 hash/size 在 [ArtifactManifest 样张](records.json)。真实 Calibre build、query database、PDK、生产平台和真实 tool command 均无运行事实。

| 核对内容 | 预期结果 |
| --- | --- |
| Source / target | 同一 `INV_M1_SYNTH`；pin order `A Y VSS VDD`；全部模型、D/G/S/B、参数和拓扑语义相同 |
| 有效 fin / finger / multiplicity | MN0：5 → 5 / 1 / 1；MP0：7 → 7 / 1 / 1；one-to-one、无 device reduction |
| 固定 FIN 背景 | 共 18 根；N 的 5 根与 P 的 7 根参与 crossing，余 6 根不被数入器件。逐根见 fixture oracle |
| 几何与连接 | 44 个 drawn records 完整保留；8 个 terminals、10 条 connector edges、6 个 components；S/D 无直连；CUT 把 LI bridge 分成两岛 |
| 规划 / 约束 | all-delta ledger 空，unsupported 空，无 candidate/repair/mutation；全 cell 10 条 mandatory toy 规则 feasible |
| Publication | baseline version 0、InitializationEvent；ECO ordered commit chain 空；geometry/semantic/occupancy/annotation/connectivity 变化均 0 |
| Lifecycle / derived | preserve/frame signatures 相同；没有 prepublication-derived layer；无 ECO 引起的 derived/view refresh |
| Core artifacts | GDS/CDL/JSON 与 frozen snapshot 语义一致；expected GDS 可因顺序不同而 bytes 不同，不能据此判几何错 |
| Validation | self-consistency、fixture oracle、audit-readiness 在声明 toy scope 内预期 pass/complete；它们不表示全部生产规则被覆盖 |
| Signoff | real Calibre DRC/LVS、Virtuoso readback 为 deferred/coverage=none；无 signoff clean 或生产 matched 声称 |

Annotation 披露：query 是 synthetic source evidence；MARK 是保留的未注释非导电 marker。`LB.left`、`LB.right` 虽同标 A，仍为互不导通的 islands，并与 gate 所在 A component 分开。这里披露 source evidence 的覆盖和孤岛，不把标签作为增加物理边的依据，也不声称 post-edit LVS match。

本例未改变目标、未选择 candidate、未执行 routing 或 resize。通过全部 required toy 检查后仍须 `requires_review`，因为这是 synthetic 工程样本。任何 required rule violation、check execution error、core export 或 required report failure 均须 reject，不能由 golden match 或 deferred signoff 掩盖。

Manifest 只标识完整可寻址的样本 export set。未来 production consumer 只能从 terminal PipelineResult/repository root 判断是否允许消费；本样张没有真实 terminal root，没有生产批准。生成时间与真实工具命令不填虚构值。
