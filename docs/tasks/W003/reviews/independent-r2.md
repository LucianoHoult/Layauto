# W004 新版样本独立 review：第二轮修复复核

Reviewer：`/root/independent_review`，未参与实现；2026-10-31。受审冻结目录 `/workspace/work/w004/review-r2/snapshot`，manifest SHA-256 为 `af14667908160f6388881c0c67cc862cecba81f78ee936f28e7817e3d68c01bd`。保留第一轮报告及原finding，不用新版成功覆盖先前缺陷。

第二轮结论：IR2–IR5已修复，IR1原两探针修复，但三个剩余单位声明冲突仍须修正。因此此快照尚不能记为全部finding闭合。几何与29个overlay的独立检查通过；后续第三轮另以新身份复核。

- `independent_check_r2.py`只使用标准库，无生成器/support导入，再次直接读取GDS REAL8/XY与CDL、精确推导40形状、8边、6本地组件、两context关联，并实际物化29份overlay。错rail现仅改expected rail为VDD，其余外部几何不变，正确隔离声明目标与实际VSS链的矛盾。
- `repair_probes_r2.py`在隔离目录修改selected owner并重绑实际header/closure。旧export profile、模型NFIN轴、nominal tick、外部异型body重叠分别拒绝为ExportProfileMismatch、UnsupportedModelAxes、UnitSourceConflict、BodyOppositeTypeOverlap，IR2/IR3及IR1原探针成立。
- 同脚本把CDL `numeric_suffixes.n.numerator`改2、`nominal_user_unit_m.numerator`改2、`canonical_tick_nm`改2，均得到`no_defect`。实际source GDS/CDL未变，重绑排除了意外hash失败。这三项属于IR1未完成的固定合同校验，已交主执行者修正。
- `raw_review`独立复核558处raw回链、10个完整polygon、27项实际文件bytes变更摘要、F2全链及6个overlay，报告 `raw/review-r2.md`。该专项也独立发现suffix/user-unit剩余冲突。
- `raw_independent_review`在其 `raw-review/review-r2.md`确认IR4 query axis/precision/quality声明冲突现在拒绝，IR5 DEVICE INFO numeric type及原文位置恢复，缺type/非numeric type均拒绝。主review将其作为独立专项结论，不冒充本人重复运行。

本轮尚未作W004最终验收、W003关闭或MR人工关闭；真实工具/产品仍未运行。下一轮应专门验证IR1三个剩余探针及受影响文档/证据身份。
