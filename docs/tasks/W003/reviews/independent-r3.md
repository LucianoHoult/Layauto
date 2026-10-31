# W004 新版样本独立 review：修复后结论

Reviewer：`/root/independent_review`，未参与实现；2026-10-31。结论：**受审新版synthetic样本范围内，IR1–IR5均已修正并复核，剩余必须修正项为0；可交PM接收实施交付。** 此结论不是W004最终验收、W003关闭、人工MR关闭或生产准入。

受审基线提交为 `9f6735dcede8e8b2135f89ff10f079a752ed758b`，最终实现快照为 `/workspace/work/w004/review-r3/snapshot`。独立核对145条manifest实际bytes，`SHA256SUMS.json` SHA-256：`9136e0509ab50e03ea260eb0d1ecaedfb4aa6a58cda17a5cc926d715de0fbd76`。r2→r3仅改变 `w003_verify.py`、W003 revision-evidence及W004新增执行段；全部fixture/raw/cache/记录/图未变。第一、二轮报告及失败复现保留，未覆盖为“从未有finding”。

## Findings处置

| 原finding | 独立复核结果 |
| --- | --- |
| IR1：唯一owner实际消费不足 | 选定units/model/规则读取或固定合同一致性校验已落实。r3在真实隔离目录重绑后，模型轴→UnsupportedModelAxes；nominal tick→UnitSourceConflict；CDL n后缀→CdlUnitContractConflict；nominal user unit及canonical tick→UnitContractConflict。三项r2残余全部拒绝，source bytes未改变。无需通用parser/config机制。 |
| IR2：export旧profile身份 | 正常profile统一为v2；回改旧profile并重绑得到ExportProfileMismatch。T04/T05/T08 source/evaluator版本同步为2。 |
| IR3：错rail见证夹带异型body重叠 | 新overlay几何与正常逐项相同，仅声明目标rail VDD；独立几何/CDL仍推出N侧VSS，目标矛盾隔离成立。另把BN.ext延至y=158的独立probe明确拒绝BodyOppositeTypeOverlap。 |
| IR4：query声明冲突被忽略 | 独立专项原axis_order、precision/raw_tick、derived quality三种重绑探针均明确失败。字段单位/quality来自所选owner或来源断言，正常558处回链成立。 |
| IR5：DEVICE INFO已知type结构缺失 | numeric type metadata恢复为opaque数字原文，normalized/source定位保留；缺行及非数字均拒绝。独立专项按legacy原文核查，未引入产品parser或修改legacy。 |

主review的 `repair_probes_r3.py`仅在冲突探针中调用受审witness，确认被测实现的拒绝行为；正向几何正确性另由无support/生成器导入的独立脚本求得。专项 `raw/review-r3.md`确认其owner残余为0；`/workspace/work/w004/raw-review/review-r2.md`确认IR4/IR5为0，r3对应输入及query helper未变化。

## 独立覆盖与证据

| W004覆盖 | 本次事实与边界 |
| --- | --- |
| R1 / V1 | 直接解析stream record bytes、REAL8 exact Fraction及XY，source/expected均单flat top、40矩形且完整tagged geometry相等；nominal/half-ULP/原整数XY链成立。完整source/target/expected CDL的top、ordered pins、globals、模型、DGSB、6参数一致。N5/P7、18FIN、LI最小50nm、M1最小5nm、local enclosure最小1nm独立计算。sources尺寸表40本地+6外部逐项一致。 |
| R2 / V1 | 本地14有效导体、8connector边、6组件；BN/BP独立，不与MN/MP本地union。上下文六形状只支持两body关联，未输出到GDS。body接续90/100nm、rail接续10/10nm、tap body/rail enclosure最小8/2nm，类型及唯一匹配成立。图的四域与实际坐标核对一致。 |
| R2/R4 / 专例 | 独立读回4-shape专例GDS，并精确计算LB−CUTB两片、A_REMOTE、3组件、平方距离4/4900/6561、最小2nm、剩余LB面积72nm²。R08/R09和同A标签保留；两片同32×16桶而不连通。其scope仅T06/T08/T10，为独立几何/annotation专例；不是完整CDL/九raw管线。W004 R2a/R4a要求的迁移目的均在，未将旧标识藏入正常raw。 |
| R3 / V2 | 两独立raw专项以integer/Fraction校验9raw、四capability、10完整polygon、146具名字段及558来源定位/lexeme/hash、17closure leaves。主review独立遍历正常/全部overlay header/closure实际hash，并独立核对records106、failures6、machine report21，共133处文件bytes及JSON pointers。 |
| R5 / V3 | 实际复制正常底座并逐例应用replacement/remove，29个overlay包含完整C01–C22及7个新body见证。逐项独立证明目标缺陷；仅C06保留声明的raw hash错误，C07为显式top错绑，未由意外hash失败遮蔽几何/语义目标。原22目的与新版表一致。不是产品typed pipeline执行。 |
| R4/R5 / V4 | policy、machine report和human report的8行检查义务逐字段一致；5个真实检查均deferred/none/requires_review及null runtime/return code。保留production downstream、Virtuoso/SKILL dry-run和未消歧virtuoso_readback分别身份。20正常/8失败组合与66非法组合为主执行辅助输出，review核对日志/样张及文件refs，不把它们称为产品结果。 |
| V5 / F1 | 独立raw专项重算27路径完整pre-context摘要，并实际改变每份文件bytes证明摘要变化；run/head/lineage/key等字段敏感性另见主执行保存输出。无尚未建立的canonical context ID。 |
| V6 / F2 | 真实DEVICE INFO缺END OF RESPONSE，坏raw→重绑header→fixture-read ToolRun→ParseResult→StageFailure/localized→失败RunRecord completed refs完整同源；原正常raw未冒充坏输入。独立专项完整核对。 |
| V7 | reviewer实际比较主执行独立生成目录与r3：116fixture文件集合及全部bytes相等；PNG SHA相等；5个记录/schema/人机报告文件相等。保存六条主执行命令、环境、stdout/stderr，返回码全0。仅重复性结论来自此比较，正确性来自上述独立计算。最终新增review附件和binary patch打包由集成人作末次重建/身份检查，不属于本145文件快照自指证明。 |

另用gdstk 1.0.2独立打开source、expected及专例：40/40/4 polygons、无references/labels、正确top。它是本地第二reader，不是production downstream gate。手写stream reader仍承担精确单位/坐标证明。

原架构、AGENTS、README、current-work、协作规则、W003原任务E/R、manual-verification及web-codex-handoff.md历史交接与基线逐字节一致；W004只有新增状态说明和E3插入，E1/E2/RP1及原正文保留。专例不补完整query子bundle的选择符合R2a/R4a几何/组件/图与规则scope要求，不构成取消R3正常raw义务。

## 可复现入口与身份

Python 3.12.14；独立精确脚本仅标准库。reader/conflict探针使用 `PYTHONPATH=/workspace/work/w004/deps` 的KLayout 0.30.12/gdstk 1.0.2；`PYTHONDONTWRITEBYTECODE=1`。

- `python /workspace/work/w004/reviewer/independent_check_r3.py`：直接GDS/CDL/几何/29overlay，脚本SHA `989c616e60f3acdff34184a96686b40237843d5779644989cd6eafb258cb8570`，结果 `independent-r3/result.json` SHA `27ee1c51af7f2a7d651f3f2ca0ede7427df29bf3fbe742e206c1f77791867e75`。
- `python /workspace/work/w004/reviewer/repair_probes_r3.py`：七项隔离修复探针；结果SHA `b78f4467f7466110a90ff591bda55a698bc8377611f6af497c147434342eab13`。
- `python /workspace/work/w004/reviewer/special_check.py`：专例独立GDS/差集/注释/同格/规则scope；结果SHA `605b7360d634c0a16f585082e33202a53e73bc6d3d59f25f68b18417a0142e7a`。
- `python /workspace/work/w004/reviewer/final_audit.py`：manifest、r2差异、尺寸、D3、133文件refs/pointers、实物再生成比较及历史保护；结果SHA `c0856c2ab9aa6fefedb8ef865efae14e9103cc66c4672ff1bc4ffd0d86cd45c9`。
- raw专项原文为 `reviewer/raw/review-r1.md`、`review-r2.md`、`review-r3.md` 及 `raw-review/review-r1.md`、`review-r2.md`；原失败与修复脚本/输出均保留。最后两专项报告SHA分别为 `8998bd81149ef3ef8e00234a2d106f5fd882ef4faccccff3b736c91e217ea457`、`578257f8fc1a9f6bc42487a413313bd353da573519a8eb77b84039e0e36d1335`。

未运行产品parser/runtime/Stage1–6、publication、完整grid/CSP/DTO/codec/CAS、生产PDK/Calibre/LVS、production downstream gate、Virtuoso/SKILL dry-run或旧readback。所有技术值为toy，production_matched_body_evidence=false、LVS not_run不变。MR-074-Q1及其他受影响人工闭合仍交PM；不由reviewer以synthetic通过代为关闭。
