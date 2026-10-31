# W004 新版样本独立 review：第一轮

Reviewer：`/root/independent_review`，未参与实现；2026-10-31。独立专项 `raw_review` 与 `raw_independent_review` 均未参与实现。基线提交 `9f6735dcede8e8b2135f89ff10f079a752ed758b`，受审固定快照 `/workspace/work/w004/review-r1/snapshot`；144条文件 manifest 全部逐字节核对，`SHA256SUMS.json` SHA-256 为 `c51894743635847a64a24cc2d87cd70206725f14b6da55019db3c4ff30bf8d64`。

本轮结论：正常几何、输入值及现有29个声明见证可独立复算，但存在必须修正项，当前不能将本轮review视为最终新版通过。主执行者正在同步附件说明/图，旧附件文字不作为本轮最终findings；最终材料及修复另行绑定新版快照复核。W004最终验收、W003关闭及人工结论归PM。

## 实际独立核验

主review运行 `PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/reviewer/independent_check.py`，脚本只使用标准库，未导入任何生成器、support parser或verifier。结果为 `independent-r1/result.json`，实际应用的29份overlay保存在同目录各case子目录。另以 gdstk 1.0.2独立打开source、expected与专例GDS；这是本地第二reader检查，不是production downstream gate。

- 直接解析实际GDS record bytes、REAL8 Fraction、XY完整顶点及element/layer/datatype。source与expected均为单flat top、40矩形，tagged geometry multiset全量相等；两UNITS字段的decoded rational、nominal delta及half-ULP绑定成立。source/expected字节不同，不把byte equality当几何正确性。
- 独立解析完整source/target/expected CDL，top、ordered pins、空globals、两device身份、model、有序DGSB和全部6参数一致。NFIN=5/7，NF=M=1，L=4n/W=2n/VT=toy；未依赖生成器的semantic答案。
- 从匹配实际stream的坐标独立计算OD去channel、FIN交叉和typed connector。得到14有效导体、8本地connector边、6本地组件；BN/BP单独，分别不与MN/MP本地union。全部8边和6组件与oracle相等。
- LI三对平方距离2500、2500、5625，最小50nm；M1六对最小平方距离25，即5nm；全部local connector enclosure最小1nm。18FIN中N5/P7完整资格与CDL一致。
- A上下文source hash/对象/类型与实际本地GDS一致。BN/BNext、BP/BPext接续边长90/100nm，两个rail接续各10nm；外部tap在body最小enclosure8nm、rail2nm，typed匹配唯一。两条支持关联与本地physical graph分列，外部六形状未出现在输出GDS。
- 29个case均在独立目录按真实replacement/remove应用；逐项核对actual bytes与header/closure，除了C06明确raw mismatch外，无意外hash错误。C01–C22原身份及目的可定位，7个新body见证的目标缺陷均存在；此结果不是产品typed pipeline运行。
- 专例GDS为4 drawn records，独立保留LB/CUTB、A_REMOTE及边界；同label两片断开目的仍存在。最终专例raw/normalized/图覆盖需结合最终交付再核对。
- `raw_review`独立标准库脚本另核对9raw、10polygon/Fraction坐标、486处真实lexeme/hash回链、27项实际文件bytes变更的request摘要敏感性、F2坏raw→header→ToolRun→ParseResult→StageFailure→failure RunRecord同源链，以及C02–05/C06/C21的实际overlay。原报告为 `raw/review-r1.md`，不把其运行冒充主review本人重复执行。

## 必须修正 findings

| ID | 问题、影响与复现 | 必要修正/当前处置 |
| --- | --- | --- |
| IR1 / R1实际owner消费 | `w003_verify.units`硬编码1nm、`parse_cdl`硬编码TOY_N/P/参数轴/n suffix，`witness`的T05/T07硬编码1与25。`load_tech`仅合并dict不能证明selected owner约束答案。隔离样本把physical模型NFIN轴改multiplicity，或formats nominal numerator改2，重绑header/closure后`witness`仍`no_defect`；见`raw/owner_probe.py/.json`。 | 固定helper也须消费唯一owner或明确核验支持合同与所选owner一致；无需实现通用配置/产品parser。主执行者已报告修正，尚待新版独立复核。 |
| IR2 / R5 profile身份 | `export_policy.json.profile_id=synthetic_static_fin_no_change_v1`，但selected tech/spec已为`synthetic_static_fin_context_no_change_v2`；binding检查不比较该字段。实际hash相符不能消除此语义错绑定。 | 同步policy身份及消费者一致性检查；涉及closure/request/report重新重绑。主执行者已报告修正，尚待新版独立复核。 |
| IR3 / body_wrong_rail隔离 | 该overlay将BN.ext扩到y=158，与BP.ext重叠20×58=1160nm²，TN.ext与TP.ext同坐标；当前T04 scope含external chain且predicate写no opposite body overlap，但helper只查本地异型body。目标rail缺陷存在，同时未披露额外几何缺陷。 | 明确规则实际适用域并核验，或重做仅目标rail声明矛盾的隔离见证。不能为得到目标issue静默放宽已声明规则。已告主执行者，待处置和复核。 |
| IR4 / R3选定方言/quality未实际消费 | 独立专项`raw_independent_review`在隔离目录分别改变header axis_order、dialect precision及derived quality并重绑，`witness`均`no_defect`；与IR1同类，但影响query精确单位/质量事实。复现见`/workspace/work/w004/raw-review/reproduce_conflicts.py`及`conflicts-results.json`，原文`raw-review/review-r1.md`。 | 明确selected dialect/header/derived registry一致性并拒绝冲突；quality来源需可回链。主review未重复该专项探针，不将其标为本人独立运行。 |
| IR5 / R3 DEVICE INFO结构 | 当前Device_Info metadata_count=1只保留layer；来源原文明确DEVICE metadata含device_type_number及seed layer，NET SHAPES才可仅layer。保留opaque语义不等于删除已知结构。原始依据及复现见`raw_independent_review`报告R3-F2。 | 保留已知type行（其值可opaque）和layer，并同步count、normalized、backlinks、失败链和所有hash；或提出可信原始格式依据说明单行DEVICE合法。本轮不能把自创删字段格式称为既有格式支持。 |

此外，T04/T08已经改为context语义，rule source/evaluator身份仍沿用旧`.../1`，应同步版本并披露新scope；不改变稳定rule ID或历史MR。该项与IR2版本闭包一并复核。

## 边界与待核验

本次读原架构§2.2、§3.4–3.6、§4.8、§5、§10.3/10.5、§12.5–12.8及W004要求，保留D1已选A、D2后置MR040、D3分项及旧readback未消歧义务。没有修改受审共享实现、原MR/W003 E/R/W004 E1/E2/RP1，没有提交推送或EDA/生产上传。

未运行产品parser/runtime/Stage1–6、repository publication、生产Calibre/Virtuoso/PDK、production downstream open/syntax、完整grid/CSP/DTO/codec/CAS。未最终核对仍在同步的图/文档、最终snapshot/binary patch及再生成证据；这些是最终review输入，不是本轮已通过事实。修复后按新快照复核受影响findings和覆盖，不自动沿用第一轮通过结论。
