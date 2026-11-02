# W007 独立代码 review

Reviewer：`/root/code_review`；专项 reviewer：`/root/code_review/dto_review`。两者均未参与方案、产品或测试实现。2026-11-02。只写 review 记录，不修改产品或代写 PM 验收。

**最终结论：通过独立代码 review，剩余必须修正项 0。** 最终受审产品与测试提交为 `0f879f01acbeac033173d0b6c6257c376bb9272a`。原 CR-01–CR-05、FR1–FR3 及执行补查 ER-01 的问题、复现与关闭过程完整保留于下文。本结论仅覆盖 W007 组件及 A1–A7 的实现/证据，不是 PM 验收。

初审 base：`8a2cdf526d6f28043fe1a59a38c3c9a9d088bf6d`（已审接口）；产品 head：`18546982984cbbbf1c29713c5b00193766fa9cd5`。本次产品 diff 为 12 文件/1,790 行新增，涵盖 normalization、domain DTO/codec 和 typing 配置。初审时 README、任务执行段与 verification 是执行者未提交草稿，未据此认定最终版本。测试初稿取 `/workspace/work/w007-tests/tests/contracts/test_w007_{inputs,contracts}.py`，其最终提交身份待集成后另记。

已读根 AGENTS、README、协作/环境规则、W007 行为与 A1–A7、独立接口方案/IR-01/IR-02、任务引用架构原文和 W003–W006 相关合同。无局部 AGENTS。重点检查真实读取适配、source/target 完整性、query 身份和 seed、C08/09/10 与 C13 阶段、DTO 跨引用、exact/provenance、canonical wire 及无 IO/发布依赖。

## 初审 findings

| ID | 等级 | 可复现问题与影响（原受审 head） | 必须处理 | 状态 |
| --- | --- | --- | --- | --- |
| CR-01 | 必须修正 | `domain/_normalization_input.py:174–188,280–291` 只证明各 lexeme 位于某捕获位置，没有闭合字段到所属记录/解释结果。对真实成功 ParseResult 同步修改 value/completed、保持 raw bytes/hash：①把 MN0.NFIN 整个参数事实替换为同文件 MP0.NFIN，归一化仍 success，MN0 从实际 5 变 7，来源跳到 MP0 行；②只对调 iXref/device_regions 的 schematic_instance 值 MN0↔MP0，保留原 field_sources，仍 success，Q17→MP0/Q93→MN0；③把 Q17 region 的 vertices_nm/bbox_nm 换成 Q93 矩形，保留原 Q17 字段来源，仍 success 输出错误 y=110..180。违反 W007 行为1/3/4/7、A2/A3/A6 与 IR-02 来源闭合。 | 验证 CDL 字段属于其 device/top 记录；query 每个具名语义/精确值与其原始字段来源及派生关系一致。仅消费已有 captures，不重读磁盘、不改变 reader/profile 容错。为这些相同文件内错拼的 DTO 添加持久回归。 | 已在最终 `0f879f0` 复核关闭 |
| CR-02 | 必须修正 | `domain/circuit.py:232–237,279–281` 验证 Net membership 完整和 sources 同文件，但不验证 sources 对应该 net 的端口/端子。正常结果把 Net A.sources 改成 VDD.sources 后，重建 Cell/source/facts/result 仍 success；A 的来源错误变成 VDD 端口与 MP0.S/B。违反完整可追溯语义、IR-02 聚合引用及 A6。 | Cell 聚合精确核对每个 net 来源集合与其有序端口及成员 terminal 的字段来源；拒绝错误、缺失或多余的其它 net 来源，并保留确定性顺序。 | 已在 `6712cbc` 复核关闭 |
| CR-03 | 必须修正 | `domain/normalization.py:211–213` 对 identity/seed 集合仅转 tuple。将合法结果的 device_identities 逆序，重建成功结果仍合法，但 record_digest 改变。初次 normalizer 排序不能保证公共 DTO/wire 的集合 canonical 性。违反已审方案“集合 canonical 排序”与 W007 行为7/A6。 | 对无序 identity/seed 集合统一 canonical 排序或拒绝非规范顺序；不能排序 ports、terminals、polygon vertices 等有序字段。补集合重排同 digest/非法非规范 wire 证据。 | 已在 `6712cbc` 复核关闭 |
| CR-04 | 必须修正 | `normalization/identity.py::admit_source` 遇所选 comparator 未实现时返回正确 `UnsupportedSemanticComparator`，但 source 指向 `tech.json`，真实声明位于 `tech/formats.json#/cdl_dialect/semantic_comparator`。真实读取测试证实该字段可由现 reader 接受后交组件判定。违反定位 issue 合同及 A6。 | 从已捕获 tech owner 关联选取实际声明文件与字段 SourceRef；核对同类 identity policy issue 的 owner 定位，不放宽 comparator/profile 能力。 | 已在 `6712cbc` 复核关闭 |
| CR-05 | 必须修正 | `domain/normalization.py::NormalizationResult.__post_init__` 的 success 守卫只校 identity/seed 覆盖，未校 source admission。真实 C09 的 NF=2 error.completed 补入同 query 的合法 identity/seeds 后，可直接构造并 wire 编码 success；真实 C10 三条 xref 仅取每个 schematic 首条形成两条 identity 也可 success；swap-X 保留 sd_swap=True 也可 success。输入原 bytes/来源及 source 参数完全不改，公开结果却能重标未准入事实，违反 W007 行为5/7、A4/A6。 | 成功 DTO 校验当前已选 profile 的 finger_count/multiplicity、swap policy 和完整一对一/no-reduction xref 关联；错误 DTO 仍可携这些未准入 completed facts。守卫是中立纯逻辑，不反向依赖 normalizer，不改变组件失败阶段。补 NF/M、swap、额外 xref 的公开构造/解码回归。 | 已在 `6712cbc` 复核关闭 |

所有 findings 已发执行者与产品 owner，要求范围内修复；reviewer 未修改实现或放宽判据。

## 初审实际验证

环境：Linux；`/workspace/.venvs/layauto/bin/python` 为 Python 3.12.14。没有运行真实 EDA。

- `PYTHONPATH=/workspace/Layauto /workspace/.venvs/layauto/bin/python -B -m pytest -p no:cacheprovider /workspace/work/w007-tests/tests/contracts/test_w007_inputs.py /workspace/work/w007-tests/tests/contracts/test_w007_contracts.py -q`：**101 passed, 1 failed，79.17s**。失败是 CR-04 所述 comparator 定位；该测试初稿仍在执行期，最终精确版本另记。
- `/workspace/.venvs/layauto/bin/python -B /workspace/work/w007-review-probes-dto/probe.py`：独立复现 CR-01 三个输入错拼、CR-02 错网来源、CR-03 identity 集合逆序 digest 变化。原输入 fixture 未改；probe 只在内存替换 DTO。
- `PYTHONPATH=/workspace/Layauto:/workspace/Layauto/tests/contracts /workspace/.venvs/layauto/bin/python -B /workspace/work/w007-review-probes-dto/relabel.py`：真实 C10 及 swap-X 经 reader/normalizer 得 error 后，公开 DTO 可重标 success；C09 NF=2 同类 probe 亦已实际运行。
- `PYTHONPATH=/workspace/Layauto:/workspace/Layauto/tests/contracts /workspace/.venvs/layauto/bin/python -B /workspace/work/w007-review-probes-dto/readback.py`：临时真实 W006 source symlink alias → prepare_inputs → repository readback → normalization success；input/result wire roundtrip 相等；再次 normalize 后 attempt 不变且 terminal=None；readback 任一 sibling 为 None 均 ValueError。没有重新解析 alias 或写入 repository。

静态核对：source/target 分立，全部 tops 与六个 canonical 参数轴进入语义；target difference 不按 resize=false 过滤，cell/device/net 结构、有序 ports/terminals/model/每轴均枚举；C13 差异归后续 planner。normalization 不 import pipeline/repository/tooling/transactions/state/legacy，Device/Net 不存几何或物理连接。上述正向检查不抵消 findings，也不代表完整 Stage2/M1 或 PM 验收。

## 修正复核与最终结论

第一轮修复产品 `cf1fe99` 已集成到含独立测试的 `df977ff3da1c10ed53bfe52998dd6f4c8e148936`。静态复核显示 CR-01/02/03/04 对应 guard 已补，但 CR-01 完整性补充和 CR-05 仍待后续修复，不提前关闭。

**CR-01-FR1（补修引入的必须修正项）：**在上述 head 的真实临时输入，把 iXref 行改为 `0 Q17 0 MN0\tX`。W005 reader 返回 success，新的 `_validate_query` 却因 `endswith(' X')` 判定 swap 而抛 ValueError；现有 reader 按 split 接受内部 tab，此输入应进入组件并返回 `UnsupportedTerminalSwap`。这属于不应收窄 W005 既有语法的修复要求，已交执行者。脚本与输出保存在 [review-evidence/whitespace.py](review-evidence/whitespace.py) / [whitespace-output-initial.txt](review-evidence/whitespace-output-initial.txt)。

**CR-01-FR2（第二轮补修复核必须修正项）：**在产品 `2f8a2d290927a21cf722cefd036e88967624be04`，将 Q17/Q93 的全部 geometry/quality/unit/precision/opaque 字段及对应 field_sources 成组互换，保留各自 record_id/layout_instance/schematic_instance 及这三项来源。每个 raw block 仍恰好消费一次、lexeme/exact/provenance 内部全部自洽，归一化仍错误 success：Q17 的 y_min=110、Q93 的 y_min=20。完整 block 覆盖不等于 query request.object/path/record ordinal 与该 region 绑定；需闭合已有 requests 的捕获事实，不能用位置集合相等代替。脚本 [seed_capture.py](review-evidence/seed_capture.py) 和 [初始输出](review-evidence/seed-capture-output-initial.txt) 保留复现。已通知执行者继续修正，不关闭 CR-01。

`6712cbcf0e00395a32836122639c79a88c3813b6` 第三轮候选复核：独立运行全部 W007 两文件测试得到 **125 passed / 85.12s**，真实 W006 alias/readback/roundtrip/attempt、FR1 tab swap 及原 FR2 单独 geometry+来源迁移均按预期通过或拒绝；旧 CR-01/05 问题脚本在非法构造处抛 ValueError。命令、输出、环境、100 文件清单的前后复核保存在 [candidate-6712cbc/final-review.json](review-evidence/candidate-6712cbc/final-review.json)。这批成功结果不能关闭下面新增复核子例。

**CR-01-FR3（第三轮补修复核必须修正项）：**专项 reviewer 在同一 `6712cbc` 候选中进一步将 `_format_metadata.responses` 前两项对调，同时做 FR2 的 geometry/field_sources 成组互换。请求捕获 bytes/hash、identity 和 record_id 来源全部保持原样。适配与归一化仍 success，MN0/Q17 y_min=110、MP0/Q93 y_min=20。FR2 guard 将 metadata 数组顺序当成 request 顺序，但只有 response 集合对比；该顺序自身没有绑定到已捕获 requests 的 path/object/record_ids。因此不能证明请求对象真正对应此 capture。已通知执行者暂缓最终通过，要求在现有安全 JSON/YAML 与捕获证据边界内修正，不重读文件或改变 W005 协议。

其余 finding 在 `6712cbc` 的复核结论如下，后续最终覆盖版本仍须核对这些代码未回退：

| Finding | 修复与实际复核 | 结论 |
| --- | --- | --- |
| CR-02 | `cf1fe99` 的 Cell 聚合按自己的 ports/terminals 重建精确 net 来源；换网来源探针在 Cell 构造处 ValueError，独立持久回归通过。 | 关闭 |
| CR-03 | `cf1fe99` 的 Facts 对 differences、identity 与 seed 集合 canonical 排序，保留有序 ports/terminals/vertices；逆序所有 identity/seed 的公共 DTO digest 相同，跨 hash-seed 回归通过。 | 关闭 |
| CR-04 | `cf1fe99` 及共享 source admission guard 从七项 tech sources 的 owner 位置选 formats/physical 实际来源；未知 comparator 的真实 W005 输入产生 formats.json 的准确字段定位，125 项内该测试通过。 | 关闭 |
| CR-05 | `2f8a2d2` 的公开 success DTO 复用纯 domain admission guard，完整消费每条 xref，并检查 model swap policy；真实 NF/M、C10 extra xref 与 swap 重标 success 均 ValueError，错误完成事实仍可保留。 | 关闭 |
| CR-01-FR1 | `2f8a2d2` 用与 reader 相同的 token whitespace 语义；真实 tab-X reader success，组件 typed `UnsupportedTerminalSwap`，来源和 swap facts 保留。 | 关闭 |

**执行补查 ER-01（FR3 wire 异常边界，必须修正）：**执行者在 FR3 产品 `d6cffa673236773b9f0aa532b52555055f26b4b5` 集成后发现，新 decoder 的 TypeError/KeyError 在 adapter 已同对象传播，但 wire `_unpack` 的外层 shape-error catch 会改包成 ValueError。Reviewer 随后在含对应测试的 `5c77f2533a1fb32b05aa6f864570fc7ee4482931` 独立运行 `/workspace/.venvs/layauto/bin/python -B -m pytest -p no:cacheprovider tests/contracts/test_w007_contracts.py -q -k captured_requests_decoder_unexpected`：**2 failed, 8 passed, 96 deselected / 5.78s**，准确复现两个 wire 用例的异常类型/对象失真；[原始输出](review-evidence/wire-decoder-output-initial.txt)。这是执行者先发现的问题，非 reviewer 的独立首发现；仍要求在保留 malformed-wire 拒绝的同时区分 decoder 意外故障，完成后复核。

以上为修正前和中间候选的真实审查过程；最终关闭依据如下。

## 最终覆盖版本与关闭回执

最终产品/测试 head：`0f879f01acbeac033173d0b6c6257c376bb9272a`。FR3 捕获请求锚定及内部模块迁移为 `d6cffa673236773b9f0aa532b52555055f26b4b5`；nested wire 异常修正为最终 head。独立接口补审见 [interface-review.md 的 FR3 段](interface-review.md#fr3-捕获请求文档锚定补审)。该补审要求已逐项对照实现与实测，原 `6712cbc` 候选不作为新版本最终通过依据。

- **CR-01（含 FR1/FR2/FR3）关闭。** CDL 记录归属/完整性、xref 与 NET NAMES 记录覆盖、region exact 值及 block 位置已闭合。最终实现仅在 `normalization._validation` 调用原 `importers.config.load_document/validate_document`，使用已经捕获且哈希匹配的 requests `SourceFile` 和所选 profile byte/depth 限额；逐项核对 request path/capability/command、object、record_id 及 polygon ordinal。原 FR3 metadata+geometry 成组交换现在得到 `REJECT request-ordered response metadata differs from captured requests bytes`。没有重读文件、另建 decoder 或修改 W005 的 JSON/YAML、Unicode、profile 或失败阶段；合法重排/Unicode/YAML 与 no-IO 正例通过。旧 domain normalization 三模块移到 normalization，domain 只保留纯语义/identity/difference 和 source-location 转换，无 importer/normalization 反向依赖。
- **ER-01 关闭。** codec 先在 constructor shape catch 之外解码 children，NormalizationInput 自身区分 shape 与 decoder 边界。adapter、input wire 和完整 result wire 上，预期 InputError 转 ValueError；RuntimeError、TypeError、KeyError 和进程中断保持同一异常对象。持久测试及专项 reviewer 额外异常探针均通过，非法 wire/schema 拒绝仍通过。
- **CR-02–CR-05 保持关闭。** 最终 148 项 W007 回归包含错网 provenance、集合 canonical、正确 comparator owner、NF/M/no-reduction/swap 公开 success 守卫以及全部原反例。源码复核确认上述 guard 在迁移后保留，wire 构造仍执行聚合校验。

主 reviewer 实际执行 `/workspace/.venvs/layauto/bin/python -B docs/tasks/W007/review-evidence/run_final_review.py`，其中完整 W007 两文件测试 **148 passed / 136.16s**。原 probe/relabel 的 exit 1 分别来自预期的 CDL 记录归属 ValueError、success xref 完整覆盖 ValueError；没有把 ImportError 计作拒绝。FR1 tab swap、FR2/FR3 拒绝、W006 alias/readback、input/result roundtrip、attempt 不推进和 5 类缺失 readback sibling 均符合预期。脚本、精确命令、输出、版本及 SHA 在 [final-review.json](review-evidence/final-review.json)。最终 probe 副本只调整已审模块迁移的 imports 与仓库定位，逻辑不变；原初审脚本仍可重建各原候选问题。

执行者的 A7 结果经 reviewer 独立核验，未冒称由 reviewer 重跑全部工程矩阵：

| 项目 | 最终实际结果与 reviewer 核验 |
| --- | --- |
| Python 3.12.14 / 3.10.22 | `tests/unit tests/contracts` 分别 **553 passed / 256.34s**、**553 passed / 342.94s**；包含 W005/W006 全回归与 IPMR-01 |
| strict typing | 两解释器均 **Success: no issues found in 33 source files** |
| 新包与安装 | 新 sdist/wheel；两套 fresh venv 安装、pip check；源码外正常/C08/C13/W006 readback/wire/no-IO smoke 均 exit 0，载入路径确为对应 site-packages |
| 版本与保护 | 独立比对 **101** 个 runtime/tests/config 工作树 SHA 与受审 Git blob；解压 wheel/sdist 各 **83** 个 runtime 文件与清单完全一致，无旧迁移模块残留；**14** 处 fixture/历史/W005/W006 保护路径与 PM 交接对象相同 |

Reviewer 实际执行 [audit_delivery.py](review-evidence/audit_delivery.py) 核对 13 项最终命令回执和包/源码身份，全部匹配；回执为 [delivery-audit.json](review-evidence/delivery-audit.json)。最终 [source-manifest.json](verification/source-manifest.json) 文件 SHA-256 为 `5fd13ce5fc1cfb6d9238bb4360027c0054e02e2487cfa8c5e0dd0b36736f2ae7`，其 content SHA-256 为 `f051ae0fecab66a1104e0aa609cc8450c1cf480a99384113027dc5a6f40976a9`。后续仅添加文档/回执的交付提交须保持该产品/测试清单不变。

判据覆盖：A1 两条真实输入链及无 IO；A2 完整模型/有序端口端子/全部 exact 参数轴与来源；A3 合法身份重命名重排及错拼/缺失/冲突反例；A4 C08/C09/C10 source 组件准入；A5 C13 channel_length 和多轴/结构变化完整目标义务；A6 immutable DTO、wire/digest/聚合引用/异常及依赖边界；A7 上述双解释器、回归、typing、构建安装与版本保护。静态检查和手写独立期望未把 fixtures expected/oracle 充作运行时事实。

未验证且不属于本切片：真实 EDA/PDK、实际提取等价或 body/physical connectivity、完整 geometry/coordinate/occupancy/state、baseline/seal、整轮 no_change/terminal、ECO 和 Stage 6。source=target 只表示该 comparator 下语义相等；C13 保留后续 planner 义务，不提前发布 pre-context terminal。**可以交 PM 进行 W007 接收；reviewer 不代写 PM 验收，不合并 main 或启动后续任务。**
