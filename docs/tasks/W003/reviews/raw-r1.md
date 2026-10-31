# W004 R3 / raw 同源专项独立 review，第一轮

Reviewer：`raw_independent_review`，未参与本轮来源调查、fixture/helper 实现或准备答案。2026-10-31。此结论只覆盖冻结快照 `/workspace/work/w004/review-r1/snapshot`；基线为 `9f6735dcede8e8b2135f89ff10f079a752ed758b`。128 个相关 fixture/helper/examples 文件已与父目录 SHA256SUMS.json 核对，manifest SHA-256 为 `c51894743635847a64a24cc2d87cd70206725f14b6da55019db3c4ff30bf8d64`。旧 README/contracts/图正在主执行者同步，不据旧文案对最终新版作结论。

结论：正常实物的 raw 数值、对象关联和已给失败链通过本专项独立检查；有两项必须修正，尚不可将 R3/V2 新版核验关闭。不是 W004 最终验收。

## 必须修正

### R3-F1：unit/quality 的声明 owner 没有被实际消费，冲突被忽略

位置：`tests/support/w004_query.py:13`、`:57`、`:78–79`，`tests/support/w004_support.py:35–48`；`query/dialect.json.geometry`、`query/header.json.query_unit`、`tech/derived.json.derived_registry[*].quality` 和 normalized 的 `field_sources`。

`normalize()` 固定解释 `(y,x)/20000 µm` 并写死 `quality=exact`，derived owner只提供名称集合；未读取声明的 dialect geometry，也未比对 header 的 axis/unit/precision。几何矩形性只能证明该组顶点可无损表示，不能证明来源声明的 annotation quality 为 exact。`unit`/`quality` 的 field_sources 只有数字/顶点，没有实际 unit/quality owner 的可解析指针和 bytes 身份。

在三个独立复制目录分别进行以下变更，重算受影响 closure bytes hash，保持 raw、正常 normalized 与 spec 原样：

1. header `query_unit.axis_order` 改为 `["x","y"]`。
2. dialect `geometry.precision` 改为 10000，`raw_tick_nm` 改为 1/10。
3. derived `toy_ngate.quality` 改为 `approximate_bbox`。

冻结实现的 `w003_verify.witness()` 三次均返回 `no_defect`。这不是旧 hash 遮蔽问题，而是绑定后的解释冲突不被识别，违背本轮 MR-004 实际消费、R3 unit/quality 来源及 D2 重复一致性要求。完整复现及目录见 `reproduce_conflicts.py`、`conflicts-results.json`、`conflicts/`。

建议：让固定样本辅助实际读取唯一 owner，并在同义重复 header/dialect/registry 字段间显式核对一致性；不足以支持 exact 的 quality 应拒绝当前 exact-only 子集或按获准语义处理，不能自动升级。normalized 需回链实际单位/quality声明；相应增加冲突见证并重新绑定生成/报告引用。不要求实现产品 parser 或泛化可配置运行时。

### R3-F2：DEVICE INFO 省掉了来源描述明确存在的 device_type_number

位置：`query/raw/device_info_Q17.txt:3–4`、`query/raw/device_info_Q93.txt:3–4`，`query/dialect.json.metadata`，`tests/support/w003_generate.py:write_raw()`。

新版 DEVICE INFO 使用 `metadata_count=1` 且仅保留 `toy_ngate`/`toy_pgate` 首层行。只读来源 `legacy_mvp/io_adapters/calibre_query.py:929–958` 明确区分 DEVICE INFO 的 metadata 包含首行 `device_type_number`、未知数量的 pin/property/optional model、最后 seed layer；“opaque”表示不解释 pin/property 语义，并非可以删除已知存在的 type 行。NET SHAPES 的资料才允许一个 first-layer metadata 行。当前实现将两种响应套成同一个最小 metadata 结构，缺少能支持这种省略的来源，削弱了 MR-034 要求的基于已有格式的单一输入路径。

建议保留至少数字 type lexeme 与首层两行 metadata，声明 type 数字为本 synthetic 例的 opaque 来源内容、不从它推断模型/端子；不需复制未知生产 pin/property 假设。若确有来源支持无 type 的 DEVICE INFO，给出版本化来源再采用。更新 count、位置回链、EvidenceRecord 和 F2 关联。真实生产方言仍待验证，不能因补此字段扩大能力声明。

## 独立执行和成功证据

运行：`PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/raw-review/check_raw.py`。脚本不 import 任何 fixture generator/normalizer/verifier；用 stdlib `Fraction`、raw 行结构、独立多输入字典关联、正交边与鞋带面积证明核对答案。

- 正常 9 raw 与 header 实际文件集合和 bytes SHA-256 一致；2 instance、4 net、2 device regions、8 net regions。
- 10 个 polygon 全顶点顺序、精确 `(y,x)/20000 µm` 换算、具名 bbox、rectangle/quality 当前值、metadata 与对象身份分别核对；D0 `[58,20,62,70]`、D1 `[58,110,62,180]`，8 net bbox 与独立表一致。
- 146 个具名字段与 486 个 raw/manifest 定位回链，逐个 SHA-256、line/token/JSON pointer、lexeme 核对通过。
- nXref＋NET NAMES 关联独立重算为 `1→n_a→A`、`2→n_y→Y`、`3→n_lo→VSS`、`4→n_hi→VDD`；index明确仅该query-run的ordinal。
- 从 site 选择和 tech owner 清单独立枚举 17 closure 叶；逐叶及 canonical aggregate SHA-256 相符。
- 独立重算 F1 canonical descriptor摘要；全部 27 个 input/raw/config/policy 文件选择齐全并匹配实际bytes。
- 独立读取 F2 坏 raw，确为正常 `device_info_Q17.txt` 删除最后 END OF RESPONSE；坏 raw hash→重绑header→独立 fixture-read ToolRunResult→ParseResult→StageFailure/localized→failure RunRecord completed refs完整同源。
- 在 `overlays/` 实际复制正常底座并应用 C02–C05 的 replacement/remove；各自目标缺陷存在、删缓存正确、所有其余 header/source/raw/closure hash 闭合。未调用产品失败管线。

独立结果为 `independent-results.json` / `independent.stdout.json`。冲突复现另运行 `PYTHONPATH=/workspace/work/w004/deps PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/raw-review/reproduce_conflicts.py`；这一步调用被审helper仅用于证明它接受冲突，不冒充独立正确性计算。

## 限制与复核

未运行真实 Calibre、产品 parser/Stage1–6、生产工具、publication 或生产上传；未把本专项扩展为所有词法/格式拒绝条件的完整 parser 测试。原 W003 E/R、MR、W004 E1/E2/RP1 未修改。修复后须对最终冻结版本核对 R3-F1/R3-F2，再交总review和PM；本报告保留原 findings，后续在末尾追加复核，不覆盖本轮原文。
