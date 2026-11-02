# W005 — 读取真实文件并核对输入绑定

把已验收的样本交给正式v2读取组件：从GDS、source/target CDL、raw query与配置读出可追溯的内容；文件缺失、格式不支持或来源不一致时给出明确错误。成功输出可供后续Stage 2消费的evidence，不从样张加载预制状态。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| 目标 / 依赖 | M1的首个产品组件切片；依赖已验收的W003/W004样本，实物基准`633e3feef8062565019838f2d270e89b7f81c4ed`。W002 E7的完整no_change闭环目标及R4首交义务保持 |
| 授权 / 阶段 | **待验收：补修技术接收通过，待main集成及最终验收记录。** IPMR-01与IPMR01-FR1均已独立复核关闭，PM核对新版本、复跑测试并接收，见[PM3](#pm3-ipmr01-receipt-20261102)。无剩余必须修正项，不重新派发已完成补修 |
| 恢复版本 | 同分支`codex/w005-input-reading-binding`，补修交付`c69018dfd1b8eb67705753bb170ec3dcebb88e8f`，最终产品/回归提交`0a6de39e02947e3ae8af64a4dca9487ee8898ca3`。接手使用包含PM3的后续PM交接提交，准确SHA见Git/回复。原实现交付`51d4d9d7b0d2715a5a2f3fe578615be4c59e74cb`、原review交付`cec15f7e3cd74f8cc439f9a5ab654597a113da78`及PM2派发`4207e773f93111ba6bfd2c6b6ac9da1eacd87fbb`保留历史身份；已验收fixture与答案未变 |
| 输出边界 | 一个可由测试及未来pipeline调用的组件API，返回不可变、经过运行时校验的配置/tech及versioned evidence、解析结果和定位信息。名称/DTO组织由执行者细化并review；本轮不发布新的稳定CLI或对外wire承诺 |
| 允许修改 | `layauto_v2/importers/`，必要的中立`domain/` evidence/results/codec类型、`tech/` schema与纯读取公共入口；`tests/unit/`、`tests/contracts/`及读取组合测试；必要依赖/typing/build配置与使用说明、本任务执行记录。新增目录按职责创建，不为所有未来模块填空 |
| 非目标 | 不实现pipeline/run入口、repository/RunAttempt/terminal publication、Stage 2 identity/spatial join与状态、规则求值/resize/导出、真实Calibre/Virtuoso获取或生产上传；不改变D1=A、MR-040后置及真实工具延期。不修改已验收fixture以迎合程序 |
| 架构依据 | [architecture](../architecture.md) §2.1–2.3、§3.1–3.2、§4.8、§5、§11.2/11.10/11.13–11.15、§12.1–12.8；架构原文优先，任务不另定产品合同 |
| 分工 / 阻塞 | 执行与独立review已交付；PM接收补修并恢复集成判断。IPMR-01/FR1技术阻塞已解除；实际main集成及组合核验尚未发生，新关键输入/能力/对外行为变化附实例交PM |

### 输入、结果与范围

1. **配置与技术资料。** 从实际site文件所在目录解析路径，读取其选择的GDS、source/target CDL、query header、body context、tech六owner及policy/limitations。仅接纳已声明版本/字段和`dummy_fixture`输入范围；校验必需项、唯一owner、跨字段/registry引用、单位/模型合同及重复outputs一致性。safe YAML/JSON拒绝重复/未知key、错误类型/版本、可执行tag、非有限数及超size/depth；阈值与测量约定须来自明确schema/profile并在测试中给边界，不照抄helper固定答案冒充通用loader。
2. **GDS。** 逐record解析当前flat轴对齐BOUNDARY矩形子集，完整保留top、element-tagged layer/datatype、原整数XY及REAL8原bytes/exact值。矩形须逐个证明lossless；支持范围外的元素、层键、hierarchy、property、非矩形明确拒绝。使用精确单位合同验证nominal scale，不能先转float再恢复精度、取整或补图。未注释MARK等可支持几何同样保留。
3. **CDL。** 解析source/target全部top、ordered pins、globals、模型、有序D/G/S/B及参数lexeme/exact值，保留文档/空依赖闭包来源。所选literal dialect之外的表达式、include、未知directive/参数及非法值明确报错。返回两份可追溯解析结果；不据5/7相等宣称no_change，不在reader做目标规划。
4. **Query。** 从实际9份raw及requests/dialect读取四种capability。落实格式内必要的nXref/NET NAMES/response关联、数量/结束结构、opaque metadata、完整polygon、坐标顺序/precision、具名exact值/quality及原文位置。区别这种格式关联与Stage 2跨GDS/CDL的语义/空间join。normalized只作可重新解析的缓存/测试期望；若提供则比较并拒绝漂移，不能作为唯一输入绕过raw。缺normalized的合法输入仍可解析；坏raw配套删缓存仍须按坏raw原因失败。
5. **绑定与来源。** 对本次实际读取bytes核验source/top、完整raw列表、netlist/deck/map/runset/include/preprocess/options闭包、body输入及tech叶子和parser/dialect版本；读取内容与校验hash必须是同一份bytes。核对query-run/database身份、tool信息、mode/classification/assurance、LVS completion/match状态的合法组合及同次输入一致性；synthetic/not_run不能仅靠重绑hash伪称真实executed/matched，未知状态如实保留。状态冲突给EvidenceIssue/ParseResult，不新增degraded默认放宽；只有已显式接纳的profile才可按架构标suspect。body context本轮只做schema、来源hash与单位/profile绑定，检查context内部ID/类型引用自洽；FRAME/BN等样本名字不来自GDS BOUNDARY，真实GDS对象定位和跨格式几何匹配留Stage 2，不引入spec/oracle作为运行时映射表，也不重算外部物理连接或输出`body_complete`。不靠文件名、同名网线或固定fixture ID推断事实。缺失/错误hash/重复或不一致绑定要定位到具体文件/字段。
6. **错误与事实记录。** 组件返回tagged config/ParseResult/EvidenceIssue等中立结果，带原因、source refs、bytes hash（仅实际读到时）、行/token/record偏移及已完成解析依据；正常/失败非法字段组合经runtime validation拒绝。期望错误不得只print或吞掉；意外异常保留根因，KeyboardInterrupt/SystemExit传播。若接收外层提供的ToolRunResult，只单向关联其id，不反写execution记录、不伪造Calibre执行。组合测试实际读文件，但不把测试driver称为产品pipeline或RunRecord。

### 验收清单

| ID | 条件 → 可观察结果 | 必需验证 |
| --- | --- | --- |
| A1 正常读取 | 已验收site→配置/tech、40个本地图形/BOUNDARY元素、两份完整CDL、四种query capability及绑定的外部context evidence | 通过组件API从实际bytes得到结果，对照独立答案/来源；expected/spec/oracle/records不得成为运行时答案输入；输入目录前后hash不变 |
| A2 精度与schema | 原XY/REAL8、CDL数值与query `(y,x)/precision`→精确值和完整provenance；修改副本不能改变返回对象 | 精度边界、重复/未知key、版本/类型、非有限数、tag、size/depth、owner/模型/单位声明冲突；最小中立codec需跨进程稳定digest且拒非法exact表示，不能使用Python hash或float作truth |
| A3 来源拒绝 | 缺输入/header/闭包/raw/context、错top/bytes/profile/单位或header运行/匹配状态组合冲突→有定位的读取/绑定错误 | 在临时目录实际应用replacement/remove；绑定故意坏与语法故意坏分开，重绑后仍检出目标缺陷，不能用意外hash错误遮蔽它；缓存删除/漂移及重绑hash后伪称真实executed/matched分别覆盖 |
| A4 格式拒绝 | 超出声明的GDS/CDL/query结构→明确unsupported/parse error，保留可读取原始证据 | 实际覆盖C01–C07、C11/C12、C17/C18、C21的所属读取/绑定目的；C09的合法NF字面量精确读出，single-finger语义准入交Stage 2，不将读取成功写成准入通过；C22及body missing-context/wrong-binding覆盖所选必需输入/算子声明与绑定 |
| A5 非单样本硬编码 | 同一声明子集内的第二个合法输入→按其真实内容读取；破坏某一输入只影响相应结果/错误 | 临时样本一致重命名top/器件/query对象、合法变换记录/参数顺序或坐标并完整重绑；独立计算期望。不能写死INV、Q17、40、5/7、9raw文件名或旧expected hash来过测试 |
| A6 可组合及隔离 | 未来调用者可以取得读取结果/错误而不建立layout state、写输出或调用EDA | importer不import tooling/state/normalization/pipeline；domain不含IO；产品代码与生产测试不import legacy或tests/support。仅迁移纯逻辑并记录来源、纠正点及parity/回归依据 |
| A7 工程首交 | 独立测试及组合读取、strict typing、wheel/干净安装可复现 | 针对新增组件的单元/合同/组合测试；选择并执行strict checker；在隔离目录构建安装并导入/跑关键读取。保留Python≥3.10，至少检查最低支持版本及实际开发版本；环境缺失写明待验证范围，不声称矩阵已通过 |

C08/C09/C10的跨证据语义cardinality/model admission、C13的目标差异、C14–C16/几何body的规则或提取失败、C19/C20输出转换等仍由后续normalization/admission/validation/export负责。W005必须保留其输入事实、列出接收方和期望阶段；不得为了凑29例全部reject把这些语义检查塞进reader，也不得把读取成功算成这些反例通过。所有pre-context失败并非都发生在Stage 1。

新输入使用预期待决：无。所选synthetic格式与D1范围已有实物及用户决定；内部API和schema校验实现细节留执行者。若现有样本与架构出现具体冲突，先给最小复现和影响交PM，不自行改架构或改golden。

## 方案与决定（执行准备，PM 接收）

### PM已确定的任务拆分

W002 E7的完整M1-P1闭环拆为可验证的组件交付和后续组合，**W005只验收读取组件**。此拆分不免除E7/R4的错误路径、typing/build及支持解释器义务：本次触及的接口同批验证，未触及的由下列后续包承担。旧[handoff](W003/handoff.md)“下一实现任务必须同批验收”的列表描述完整M1范围，不能将其中Stage 2–6自动塞进W005，也不能视作已完成。

| 后续组合任务 | 不得遗漏的义务 / 启动条件 |
| --- | --- |
| 输入组件接入pipeline及pre-context审计 | 任何正式run入口须在解析前经repository创建unsealed attempt；串联真实fixture读取的ToolRunResult与ParseResult。失败经StageFailure→最小failure RunRecord→terminal（含freeze/terminal失败与interrupt边界），绑定F1全request及F2真实坏raw；不能用W005结果替代run记录 |
| Stage 2与baseline/no_change | identity/spatial join、完整坐标/occupancy/connectivity、body/extraction/mandatory规则；完整初始化、seal、phase/revision/CAS/幂等及不可变性。样张expected JSON不是完整snapshot |
| Stage 6及完整M1组合 | 实际只读GDS/CDL/JSON导出、独立读回、Manifest、人机报告与terminal；输出精度/overflow、required failure和全部run生命周期错误验证。组合通过前不宣称M1完成 |

该表分配既有义务，不在本轮派发多个产品任务。MR-040配置机制精简另在改变当前入口/优先级前给具体取舍；旧Virtuoso readback在真实工具集成前明确，真实准入G1–G5按原里程碑保留。

### 执行起步

读取当前v2骨架与上游输入/下游consumer合同，先在本节补一页组件API/DTO、错误与边界验证设计，并请未参与实现者检查依赖方向和Stage 1/2分界。既有范围内review修正后直接实施，不为普通内部接口再造用户审批；代码完成再做独立review。定向查看legacy CDL/query纯格式逻辑与测试，拒绝float-round、固定fixture答案、convenience JSON和归档runtime依赖；W004 helper仅作为行为参考/测试支撑，不能整包复制成产品parser。

### E1. 组件方案（2026-11-02）

W005 API/DTO/error plan v1 (implementation preparation; no acceptance claim)

Public read_inputs(site_path: Path, *, tool_run_id: str | None = None) -> ParseResult.
Lower-level parsers consume SourceFile (immutable uri, exact bytes, sha256) plus validated immutable profile maps; they never read disk or infer names. read_inputs owns a per-call byte store, resolves every site selection against site parent, hashes and parses the identical bytes, and retains all actually read sources and successful component evidence on failure.

Neutral domain codec: recursive FrozenMap/tuple values; only None/bool/int/str/bytes/Fraction and immutable containers. freeze() defensively copies mappings/sequences; canonical codec encodes bytes/rationals with tagged exact representations, sorted string keys and ordered arrays, SHA-256 (no float/Python hash); decoder rejects invalid/noncanonical exact representations. Evidence: versioned EvidenceRecord(kind, payload, source_refs, parser_version); SourceRef(uri, sha256 when read, field/line/column/byte_offset/record_index as available). ParseResult tagged success/error, runtime checks disallow success with issues or failure with final value; completed component evidence always separately available. EvidenceIssue has read/config/parse/unsupported/binding category, stable reason code, source locations. Internal InputError is converted by public facade; only known OSError/Unicode/format exceptions handled, unexpected exceptions retain traceback; KeyboardInterrupt/SystemExit propagate. Optional tool_run_id is a one-way immutable link only.

Components: safe config loader + tech schema with recursive closed schemas and owner/registry/units/model checks; stream-record GDS parser with original integer vertices and REAL8 bytes/rational/nominal/delta; CDL source+target full document, tops/pins/globals/models/ordered terminals and all parameter lexemes/exact values; query parser for four capabilities from header raw descriptors and explicit request manifest, preserving opaque metadata, complete polygons, named exact provenance and format-level association; binding/context reader validates actual-byte closure, source/top/profile/unit, synthetic status combinations and context internal references.

Schema/profile input limits: bootstrap schema layauto-input/1 hard ceilings max text bytes 1,000,000, nesting depth 32 (root container depth 1), records 1000, matching current formats limit declaration; profile may tighten, never exceed implementation ceiling. Every text byte includes whitespace/newline; depth counts mappings/sequences. Known profile IDs select implemented grammar, supported fields checked recursively. Object IDs/top/filenames/counts/coordinates remain data. Future schema versions require explicit support; no permissive fallback.

Normalized query files are optional cache only: parse all raw first, compare a freshly reconstructed w004-query-normalized/2 cache representation if each conventional capability cache exists; absent cache allowed, malformed raw still fails by its own reason. Profile contract version differs from product parser implementation version. No expected/oracle/spec/records runtime reads.

Tests: accepted bytes and independent answers, negative overlay files and explicit rebinding to isolate parse vs hash errors, all A1-A7 including second legal renamed/transformed source, mutation-alias attempts, cross-process digest, strict mypy, wheel clean install and actual interpreter versions. Fixtures never modified; Stage 2-only negative cases remain parsed facts with deferred receiver list. No pipeline/state/EDA/export or body_complete computation.

接口 review 记录见 [W005/interface-review.md](W005/interface-review.md)。最终代码 review 另记，不以方案 review 代替。

## 执行结果（执行）

### E2. 实现与验证交付（2026-11-02，执行）

本轮由用户明确授权完整实现、独立 review、提交及推送；结果交 PM 接收，**未自行验收 W005、合并 main 或启动后续任务**。任务阶段、current-work 与 PM 段保持 PM 归属。

恢复时 `/workspace/Layauto` 位于 `work` / `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，staged/unstaged/untracked 均为空。显式 fetch 后切到 `codex/w005-input-reading-binding`，起点精确为 `5b7205009b3ed7f8fe15e135e674654f2f544557`。已逐项读取 AGENTS、README、协作规则、current-work、本任务、引用架构及 W003 contracts/实际输入。检查到仅根 AGENTS，无局部追加规则。初始网络默认沙箱代理不可达；使用受支持的网络权限访问同一代理后同步成功，未绕过网络策略。

独立接口 review 通过后，由主执行统一集成；GDS/CDL、query、config 与测试分别在独立 branch/worktree 实现。共享中立合同先发布，各 worker 提交经 cherry-pick 集成；最终 reviewer 未参与实现。运行组件的最终受测/受审提交为 **`ab7feddff83749b54c1866b1ad95fbc99fd787f1`**，之后的交接提交仅保存文档与验证记录。22 个实现/测试/构建/说明文件的实际 SHA-256 见 [source-manifest.json](W005/verification/source-manifest.json)。完整可恢复内容由该提交及最终分支提交提供，不依赖临时 worktree。

实际交付入口为 `layauto_v2.importers.read_inputs(Path(...), tool_run_id=...)`。中立 `SourceFile/SourceRef/EvidenceRecord/ParseResult/EvidenceIssue`、递归不可变 exact codec、safe schema/tech owner、GDS/CDL/raw query parser 与同次 bytes 绑定共同形成只读组件。输入失败返回 tagged error，保留已读 bytes/hash、定位及已完成组件；意外异常与 KeyboardInterrupt/SystemExit 传播。`tool_run_id` 仅单向关联外部记录。接口用法及限制见 [README](../../README.md#input-reading-component)。

定向调查了 `legacy_mvp/io_adapters/cdl_parser.py`、`calibre_query.py` 与 W004 helper 的格式/缓存约定；实现依据声明 grammar/profile 重新编写，没有迁移或整包复制 legacy/helper 代码。明确纠正 legacy float/suffix-round、忽略未知记录、single-top collapse、固定名字及 convenience JSON 路径；完整 normalized 缓存 parity、独立手写答案及错误回归作为依据。产品与产品测试没有 import legacy 或 tests/support。

| 验证项 | 实际结果与可访问依据 |
| --- | --- |
| A1 实际输入 | 从 site 读取配置、六 owner、40 个 BOUNDARY（包括未注释 MARKER）、完整 source/target CDL、四类 query 2/4/2/8 records、绑定只读外部 context。独立几何/CDL答案仅由测试读取；拦截文件打开证明产品不读 spec/oracle/expected，输入目录前后全文件 hash 相同。见 `test_accepted_actual_files_match_independent_answers_without_runtime_oracles`。 |
| A2 精度/schema | 保留 XY、REAL8 bytes/exact/nominal/delta、CDL lexeme/Fraction、query `(y,x)`/20000 与 1/20 nm 边界；未知/重复 key、版本、类型、tag、float/NaN、size/depth、owner/模型/单位/registry 冲突均测试。codec 拒绝非规范 rational，跨进程 digest 稳定；nested alias 修改不改变返回值。profile 不能改写已声明固定 1 nm source nominal。 |
| A3 来源拒绝 | 实际复制/替换/删除输入；缺输入/closure/header/context、错 hash/top/profile/单位、重复绑定及 synthetic 假 executed/matched 被定位拒绝。完整重绑后语法缺陷仍命中目标错误；删除 cache 不绕过 raw。额外验证一次读取后磁盘变化不影响已捕获 bytes/hash/parser 同源性、绝对路径与合法 URI 重命名。 |
| A4 格式边界 | C01–C07、C11/C12、C17/C18、C21/C22、missing_body_context/body_wrong_binding 均覆盖所属错误。C09 的 NF=2 精确保留。其余后置案例读取成功仅证明事实保留，接收方见下表；不声称全29例均在 reader 拒绝。 |
| A5 第二输入 | 一致重命名 top、器件/query identity、全部 raw 文件路径与 record IDs；改变 NFIN、平移坐标、反转 record/顶点/参数顺序并完整重绑；结果按独立计算读取。另加第41个未注释 BOUNDARY仍保留，证明不写死40图形。 |
| A6 组合/隔离 | 无 pipeline/state/normalization/tooling/legacy/support runtime import，无 EDA/写输出/状态构造；AST边界检查通过。body只验证内部ID/角色引用及来源单位profile，BTAP_N→BTAP_P等物理兼容判断仍保留后续。 |
| A7 工程 | Python3.10.22最终完整 **237 passed**；Python3.12.14独立 reviewer 对同提交完整 **237 passed**（执行者此前f29c84a为236 passed，新增缓存权限回归另复核）。strict mypy针对13个产品模块通过。sdist/wheel重建成功；新3.12环境安装完整依赖、`pip check`及源码目录外`-I`正常/重绑坏raw smoke通过。既有fixture-support另为3 passed、8 subtests。 |

### E3. 可复现命令、review处置及限制

环境：Linux x86_64；开发 Python3.12.14，最低支持版本 CPython3.10.22。工具环境 `/workspace/work/w005-venv`、最低版本 `/workspace/work/w005-py310-venv`；均在仓库/用户home之外。以下命令在仓库根执行，`python`分别选择对应环境；使用README所列 `.[dev]` 可重建测试工具。

```sh
python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q
python -m mypy
python -B -m pytest -p no:cacheprovider tests/fixture_support -q
python -m build --outdir /workspace/work/w005-dist-final .
python -m venv /workspace/work/w005-wheel-env
/workspace/work/w005-wheel-env/bin/python -m pip install /workspace/work/w005-dist-final/layauto-0.2.0-py3-none-any.whl
/workspace/work/w005-wheel-env/bin/python -m pip check
# 在源码目录之外执行，传入实际 fixture 绝对路径：
/workspace/work/w005-wheel-env/bin/python -I /workspace/Layauto/docs/tasks/W005/verification/wheel_smoke.py /workspace/Layauto/tests/fixtures/w003_m1
git diff --check 5b7205009b3ed7f8fe15e135e674654f2f544557
```

[验证索引](W005/verification/receipt.json)保存版本、命令、结果和产物 hash；[最低版本完整日志](W005/verification/pytest-310-final.txt)、[strict日志](W005/verification/mypy.txt)、[构建](W005/verification/build-final.txt)、[安装](W005/verification/install-wheel.txt)、[pip check](W005/verification/pip-check-wheel.txt)、[wheel smoke](W005/verification/wheel-smoke.txt)随Git交接。Python3.12最终独立完整复跑见 [代码review](W005/code-review.md)；之前执行者完整日志仍保留原236项身份，没有改写成237项。最低版本首次检查发现4项测试instrumentation在Python3.10未拦截Path.open，修正测试入口后定向及最终全量复跑均通过，没有放宽产品断言。

执行方已按review修复：缓存用canonical exact bytes比较以拒绝bool/int类型漂移；body context按tech声明role检查内部引用；closure编码只接受真实计算的UTF-8约定；循环符号链接及可选cache权限错误进入typed read error。另补NUL路径、固定source单位、键序无关性和实际权限回归。原finding及独立复核结论由 reviewer 保存在 [代码review](W005/code-review.md)，本段仅记录执行处置。

| 已读取事实 / 后置案例 | 接收方与仍需验证的义务 |
| --- | --- |
| C08、C09、C10 | Stage2 normalization/admission：跨CDL/query cardinality、single-finger、reduction；reader不代做准入。 |
| C13 | Stage2目标解释及Stage4能力规划：完整target差异，不能把reader成功写作no_change。 |
| C14–C16与body类型/断开/歧义/enclosure/rail案例 | Stage2 extraction/connectivity及后续mandatory规则；context内部ID/角色schema检查不等于物理匹配或body_complete。 |
| C19/C20 | Stage6输出representability/overflow，源文件读取不提前执行导出。 |
| 全部正式run | 后续pipeline需unsealed attempt、ToolRun/Parse单向关联、失败RunRecord/terminal及Stage2状态与Stage6完整组合。本组件不替代这些硬门。 |

未验证/不在本轮：真实Calibre/Virtuoso/PDK、matched/live assurance、生产准入、目标平台/macOS/Windows及除3.10/3.12外的解释器矩阵；3.10已实际执行完整组件测试，干净wheel安装本轮在3.12验证。没有宣称真实工具运行、完整M1或pipeline通过。现有fixture、答案、support、architecture与current-work相对起点无改动；legacy未运行或修改。待PM核对本分支实际SHA、证据、finding复核及任务范围后作最终接收决定。


### E4. 发布身份更正（2026-11-02，执行）

首次推送被 GitHub `GH007` 邮箱隐私保护拒绝，远端 W005 未改变。仅将本轮尚未发布的14个提交的author/committer邮箱改为仓库已有的 `LucianoHoult@users.noreply.github.com`；提交tree、message、日期及父链顺序保持不变，没有改动既有起点或使用force push。

完整旧→发布身份及每个相同tree见 [publication-map.json](W005/verification/publication-map.json)。原受测/受审产品提交 `ab7feddff83749b54c1866b1ad95fbc99fd787f1` 对应可发布提交 **`cf35d97478cd78aa7ad707d18c9e37ceda10eafb`**，共同tree为 `70b905b98691ddcdf58726810ca875dc853069c2`。原始执行日志、manifest和review保留实际发生时的本地SHA；通过此映射可在远端分支恢复相同完整内容，不能将邮箱元数据变化写成重新运行产品测试。Reviewer另在代码review追加独立内容身份复核。最终推送tip及远端核验SHA见执行交接回复；它还包含本段和发布映射记录。

### E5. IPMR-01 局部补修（2026-11-02，执行）

起始核对：预置 `/workspace/Layauto` 为干净的 `work` / `87fe5a5a87d0cbb1f97952f1485dac9a71416369`。获取指定远端分支后确认其完整 SHA 为交接 `4207e773f93111ba6bfd2c6b6ac9da1eacd87fbb`，切换到 `codex/w005-input-reading-binding`，无既有 staged/unstaged/untracked 改动。适用规则仅根 AGENTS；读取 README、协作/环境规则、PM2、原独立报告及架构 §2.2、§11.2/11.10/11.15、§12.1/12.6 等受影响合同。

先在交接版本、CPython 3.12.14 执行原报告三用例，得到相同两条 `UnicodeEncodeError` 路径和成功的直接 UTF-8 对照；原脚本及实际输出另存 [original_repro.py](W005/ipmr01-verification/original_repro.py)、[repro-before.txt](W005/ipmr01-verification/repro-before.txt)，原报告未改写。

方案与实现：仅在 `importers/config.py` 的 safe document 字符串边界把 high/low surrogate pair 转为对应 Unicode scalar；孤立、反序、不完整配对返回 `InvalidUnicodeScalar`，带实际 source hash 及 scalar 起始行/列。key/value 递归共用该处理，重复 key 在解码后检查。保留原 codec 算法和 facade 的 InputError 捕获边界；不替换或忽略字符。已有 source 捕获及 completed 累积机制因此可直接保留失败证据。

新增两份持久回归文件 `tests/unit/test_w005_unicode.py`、`tests/contracts/test_w005_unicode_inputs.py`：包含原三用例、非 BMP 首尾边界/连续配对、嵌套 key/value、非法序列、两种顺序重复 key、YAML/字面反斜线、unknown key，以及 public API 的 bytes/hash/定位/九项 completed 和成功 payload digest。仅写临时副本，site 变体完整重绑；比较解析后的 config 语义，不要求不同原 bytes/header 的完整结果 digest 相等。开发解释器首次新增回归实际 **34 passed in 4.12s**。

第一版补修提交 `9c899c7be309c17931eec656ebdb46482ccb3909` 在开发版完整 271 项、mypy 13 模块、3.10 受影响 107 项及构建/安装中通过，独立 reviewer 另发现同一边界的 IPMR01-FR1：YAML 八位 Unicode escape 超出 U+10FFFF 时，PyYAML 的 chr 在节点创建前抛裸 ValueError/OverflowError。接受为 PM2 范围内必须修正项；第一版日志以 `*-r1.txt` 和 [r1-identity.json](W005/ipmr01-verification/r1-identity.json) 单独保留，不用于证明后续改动。

第二次局部修复在 SafeLoader 的 flow scalar scanner 窄边界识别正在处理的越界八位 `\U` escape，转换为带原 mark 和根因的 ScannerError，再沿既有语法错误路径返回 `InvalidDocumentSyntax`。只有双引号、当前位置前为 `\U`、八位十六进制且值越界时才转换；其他 ValueError/OverflowError、程序错误与进程中断继续传播。新增 key/value、public API 原 bytes/hash/completed、边界合法最大标量与异常传播回归。最终验证及 reviewer 复核按下列补充记录交接；原 fixture、答案、support、codec、历史报告与 PM 状态保持。


**最终受测产品/回归提交：`0a6de39e02947e3ae8af64a4dca9487ee8898ca3`。** [补修验证回执](W005/ipmr01-verification/receipt.json)记录命令、环境、实际输出与 hash；[source-manifest](W005/ipmr01-verification/source-manifest.json)覆盖 77 项产品/测试/配置/说明文件，67 项 wheel 产品文件与提交逐项相同（含 `py.typed`）。后续仅追加执行/review 证据的提交不冒称重新测试产品。

| PM2 验证 | 本次实际结果 |
| --- | --- |
| 原报告三用例、持久回归 | 修复后 cache 返回 `InvalidUnicodeScalar`，escaped/literal note 均为 U+1F600 且 digest 成功；新增 47 项持久回归包含在以下完整/最低版测试中。见 [repro-after](W005/ipmr01-verification/repro-after.txt)。 |
| CPython 3.12.14 完整组件 | `python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q`：**284 passed in 34.05s**。见 [完整日志](W005/ipmr01-verification/pytest-312.txt)。 |
| Strict typing | `python -m mypy`：**13 source files，无问题**；采用项目 strict/3.10 配置。见 [mypy](W005/ipmr01-verification/mypy.txt)。 |
| CPython 3.10.22 受影响回归 | safe config、新增两文件、既有中断/意外异常、cache bool/int 与 key-order 回归：**120 passed in 13.22s**；准确选择见 [命令和日志](W005/ipmr01-verification/pytest-310.txt)。 |
| 新构建及干净安装 | 从受测提交 `git archive` 到仓库外，隔离 PEP517 sdist→wheel 成功；全新 3.12 venv 安装完整声明依赖，`pip check` 通过。见 [build](W005/ipmr01-verification/build.txt)、[install](W005/ipmr01-verification/install-wheel.txt)、[pip check](W005/ipmr01-verification/pip-check-wheel.txt)。 |
| 安装来源及实际读取 | 源码目录外 `python -I -B .../wheel_smoke.py <fixture>` 通过；导入为新环境 site-packages，安装 config SHA 与受测源一致。正常 40 图形/8 net regions、三种非法 escape × key/value 的 bytes/hash/定位/九项 completed、两种合法 note 的 config 等价/全 payload digest、解码后重复 key 均断言。见 [脚本](W005/ipmr01-verification/wheel_smoke.py)、[输出](W005/ipmr01-verification/wheel-smoke.txt)。 |
| 范围及历史保护 | `git diff --check` 通过；fixture/答案/support/architecture、原 verification/三个 review 报告、current-work/roadmap 相对交接 SHA 无 diff。原报告和第一版补修日志未覆盖。 |

本次未重跑 3.10 全套或在 3.10 做干净 wheel 安装，未验证其它解释器/平台、legacy/fixture 生成、真实 EDA/PDK/生产、pipeline/Stage 2/Stage 6 或完整 M1。独立 reviewer 的结论另见 R3 和其报告；交回 PM 决定集成/验收，执行者不改 PM2 状态、不合并 main 或删除分支。

## Review 结论（reviewer）

### R1. 独立接口与最终代码复核（2026-11-02，reviewer）

`interface_review` 对 E1 方案独立复核后允许进入实现，记录见 [接口review](W005/interface-review.md)。未参与产品实现或测试编写的 `final_review` 另对 base `5b7205009b3ed7f8fe15e135e674654f2f544557` 至最终实现 `ab7feddff83749b54c1866b1ad95fbc99fd787f1` 完成代码、实际输入、错误路径与 A1–A7 证据复核；[完整报告](W005/code-review.md)保留五项原始 finding、修复及独立关闭依据。**无剩余必须修正项，交 PM 接收；不代替 W005 最终验收。**

Reviewer 直接运行最终 Python3.12 完整组件测试 **237 passed**、strict mypy **13 source files**，并在 Python3.10 复跑10项相关修复回归。已对照执行者最终3.10完整237项、构建安装日志和22文件manifest；独立核验最终wheel与受审产品文件相同，并从源码目录外以安装环境`-I`运行正常及重绑坏raw读取。原fixture/答案/support/架构/current-work未改写。pipeline、Stage2状态/物理匹配、Stage6导出及真实工具/生产验证仍按任务边界后置，读取成功不等于其准入通过。

### R2. 独立合并前复核（2026-11-02，reviewer）

对 base `5b7205009b3ed7f8fe15e135e674654f2f544557` 至实际 head `787a09e269062dd5c31df8ced627a6ecb799df57` 完成新一轮独立代码与合同复核，见 [独立合并前报告](W005/independent-premerge-review.md)。本次新环境完整组件测试 **237 passed**、strict mypy **13 source files 通过**，发布身份与既有最低版本/构建证据已核验；另在仓库外副本复现 **1 项 P2 必须修正项 IPMR-01**：转义 surrogate 字符可导致缓存校验抛裸 `UnicodeEncodeError`，并使成功配置 evidence 无法 canonical 编码。**当前不具备合并条件，交 PM 安排修复及独立复核。** 保留 R1 和 PM 接收历史；本轮不改产品实现、不代写最终验收。

### R3. IPMR-01 局部补修独立复核（2026-11-02，reviewer）

未参与本轮实现或生产回归编写的 `ipmr01_review` 在独立 detached worktree 对交接 `4207e773f93111ba6bfd2c6b6ac9da1eacd87fbb` 至最终产品 `0a6de39e02947e3ae8af64a4dca9487ee8898ca3` 定向复核；执行证据提交 `9ff519c1e9f04f360b649b5e93a1e05ddd6ff9c2` 未再改产品/测试。详见 [补修独立报告](W005/ipmr01-fix-review.md)。首轮 reviewer 发现八位 Unicode escape 越界仍抛裸 ValueError/OverflowError，记作 IPMR01-FR1；原始事实、修正版本和关闭依据均在新报告保留，原 IPMR-01 报告未改写。

**最终 IPMR-01 与 IPMR01-FR1 均可关闭，剩余必须修正项为 0，交 PM 核对集成/验收。** key/value 合法配对、解码后重复 key、非法 Unicode 的 typed 错误、实际 bytes/hash/定位及九份 completed evidence、成功 value/全部 payload 的 canonical digest 与异常/中断传播均已核查。Reviewer 直接执行 Python 3.12 定向 **50 passed**、Python 3.10 新增 **47 passed**、strict mypy **13 source files**、原三用例及独立 Unicode 探针；采用并核验执行者最终完整 **284 passed**、3.10 受影响 **120 passed** 和新构建/安装日志。

独立核对 77 项 source manifest、23 项证据 hash，以及新 wheel/安装目录 67 项产品文件与受审提交一致，并在源码目录外以安装环境 `-I -B` 复跑正常及关键缺陷 smoke。旧 fixture、答案、support、原 review/verification 与 PM 状态保持；本轮未重跑 3.10 全量/干净安装、其它平台或真实工具，不扩展 pipeline、Stage 2、Stage 6 或完整 M1，也不代替 W005 最终验收。

## PM 验收与交接（PM）

<a id="pm1-receipt-20261102"></a>
### PM1. 读取组件分支技术接收（2026-11-02）

**接收51d4d9d的W005读取组件及A1–A7证据，未发现剩余必须修正项；main集成和最终验收尚未发生。** 已取得实际提交，核对39个变更路径及原输入/答案/support/架构未变。`w005_scope_acceptance`只读对照实际组件、测试及Stage 1/2边界，并独立复现原R1–R5修复后的准确错误；`w005_evidence_acceptance`核对22项source manifest、13项证据hash及14个已发布提交的tree/父链。接口方案正文可从E1恢复至原review哈希；交付tip与发布产品提交的22项受审文件完全相同。

PM在本环境Python3.12.14实际复跑完整组件测试：**237 passed**；strict mypy：**13 source files，无问题**。从51d4d9d的git archive在独立目录重建sdist/wheel，wheel内14项产品文件与受审manifest一致；全新3.12环境安装完整依赖，`pip check`通过，在源码目录之外以`-I -B`运行已入库smoke，正常40图形/8个net region及重绑坏raw的`MissingTerminator`均通过。命令、原始结果、重新构建wheel身份及证据核验摘要见[PM接收回执](W005/pm-receipt.json)。本次重建的是新wheel，不冒称重验原执行者wheel。

Python3.10完整237项采用已核验身份的执行日志及独立review记录，本PM未另装3.10重跑；原3.12执行日志的236项历史身份保留，最终237项由原review及本轮实跑分别支撑。原14个未发布commit对象和原wheel不在本环境；原/发布email元数据等价及原wheel核验采用已刊独立review事实，本轮直接证明发布树、manifest与当前受测代码一致。未将这些限制变成新的实现或确认门。

本次只同步PM状态/恢复入口、路线图和接收回执，保留E1–E4、R1及两个原review附件；未修改产品、测试或fixture。组件读取结果只表明格式/来源/绑定成立，pipeline生命周期、Stage 2状态/物理匹配和Stage 6导出及真实工具仍未实现或验证，完整M1尚未通过。

下一步是安排W005合入main并记录集成版本及组合检查，再准备输入组件接入正式运行审计的近期任务；不重开W003/W004，不把所有Stage 2或Stage 6工作塞进本次组件验收。本轮不合并main、不创建或启动下一产品任务。

<a id="pm2-ipmr01-20261102"></a>
### PM2. 接收独立合并前review，派发IPMR-01补修（2026-11-02）

**接收[独立报告](W005/independent-premerge-review.md)的IPMR-01，P2必须修正，暂缓合并。** 远端review提交已核实为`cec15f7e3cd74f8cc439f9a5ab654597a113da78`，仅增加报告及reviewer记录；main仍为`87fe5a5a87d0cbb1f97952f1485dac9a71416369`。PM1及原R1–R5保留当时事实，当前判断以本段为准。

PM在该提交、Python3.12.14环境实际运行报告中的完整三用例脚本：cache抛`UnicodeEncodeError`；escaped_note返回success但digest抛同类异常；literal_note成功且可digest，与报告一致。命令为报告复现代码使用`/workspace/work/w005-pm-check-env/bin/python -B`运行；只写临时副本。本轮未重跑237项或mypy，相关通过数采用独立报告并明确其未覆盖此缺陷。只读专项`w005_ipmr01_scope`另核对字符串key/value及解码后重复key边界，支持原P2。这是既有safe-load、typed错误及canonical evidence义务内的修复，不新增产品需求或重开样本验收。

**修复范围与关闭条件：**

1. 在文档字符串解析边界一致处理key/value。合法JSON surrogate pair应得到对应Unicode字符，与直接UTF-8表达的语义一致；孤立high/low surrogate、错误顺序或不完整配对应返回有来源和定位的`InputError`。具体helper和错误码由执行者选择；不能只包住缓存比较，也不能全局捕获异常、忽略/替换字符，或通过改变既有canonical编码算法掩盖问题。
2. 解码后仍拒绝重复key：同一字符分别以转义和直接形式作为key时不能静默覆盖。合法非BMP字符应继续接纳，不因补修统一拒绝。保持原有未知key/schema、size/depth、精度及来源绑定规则。
3. 公共`read_inputs`缓存错误须返回typed error，定位到实际缓存并保留其原bytes/hash，以及失败前已完成的组件evidence。合法转义配置须读取成功，最终value与已完成evidence的payload均可canonical编码/digest。转义/直接表达的**解析语义payload**应等价；原始文件bytes/hash和重绑header本就不同，不要求两个完整结果的digest相同。
4. 将原报告三用例及上述key/value、重复key边界变为持久回归；只修改临时输入副本，需要时完整重绑，断言具体错误而非任意失败。非法缓存用例需断言completed保留和原bytes/hash，不被更早的hash错误遮蔽；意外异常和进程中断继续传播。已验收fixture、oracle/expected、support和原报告不改写。
5. 在当前开发解释器跑新增回归、完整`tests/unit tests/contracts`及strict mypy；最低支持Python3.10补跑受影响回归，保留实际版本/命令/输出。产品文件改变后从补修版本重建wheel并在干净环境做正常读取及本缺陷关键用例，核对安装来源。旧237项、旧wheel与旧manifest只能证明旧版本，不覆盖新改文件；新增验证记录单独保存，不覆盖历史证据。环境缺项如实记录并交PM，不虚报通过，也不机械重跑无关fixture生成/legacy/EDA。

**交接与写入责任。** 沿用独立执行session；允许修改必要的`importers/config.py`及确有需要的相邻中立合同、相关`tests/unit/`/`tests/contracts/`、本任务执行段与新增补修证据。实现前先复现并记录简短方案；既有范围内直接修复，无需重新开全量接口设计。执行者追加E5，保留原finding和PM状态；由未参与实现者在明确修复提交/文件身份上定向复核，报告写入`W005/ipmr01-fix-review.md`并在本任务reviewer区追加结论，说明是否可关闭IPMR-01，不代写最终验收。核查受影响结论，不重做全项目review。

完成后将补修、测试、执行/review记录提交推送到同一W005分支，沿用项目既有GitHub noreply身份，核对远端完整SHA；如远端有新提交先核对并安全集成，不force push。交回PM修复版本、关闭依据、实际验证和未执行范围。**不合并main、不删分支、不启动下一产品任务。** PM核对新交付后再决定集成及验收；本次PM仅更新任务/入口，未修改产品或宣称问题已关闭。

<a id="pm3-ipmr01-receipt-20261102"></a>
### PM3. 补修技术接收，恢复集成判断（2026-11-02）

**接收`c69018dfd1b8eb67705753bb170ec3dcebb88e8f`，确认IPMR-01与IPMR01-FR1关闭，无剩余必须修正项。** W005恢复待验收，已满足本轮补修及合并前技术要求；main集成和最终验收仍待实际执行。原IPMR-01报告、PM2派发时的开放状态和首轮FR1发现保留为历史事实，不再作为当前未关闭问题。

核对交接`4207e77`至当前交付：产品仅修改`importers/config.py`，新增两个回归文件，其余为执行/review证据。合法pair统一解码后再检查key重复，非法surrogate返回定位错误；FR1仅在scanner确认越界八位转义时转换已知底层异常，其他程序错误和中断传播。没有改变codec算法、既有输入来源合同或Stage 1/2边界。已验收fixture/答案、support、架构及原review/verification均未变。

PM在本环境CPython3.12.14、PyYAML6.0.3直接复跑最终代码：完整`tests/unit tests/contracts` **284 passed in 29.86s**，strict mypy **13 source files通过**。原报告三用例变为缓存`InvalidUnicodeScalar`、两种合法note成功且可digest；另运行已入库独立探针，256项合法标量、4096项孤立surrogate key/value、64项重复key、128项越界转义和4项公共缓存用例全部通过，错误保留原bytes/hash/定位和九项completed。原始输出、环境、命令及身份核验另存[PM补修接收回执](W005/ipmr01-pm-receipt.json)。pytest仅有一项第三方anyio弃用提示，无失败。

只读证据专项`w005_fix_receipt`重算23项证据hash及77项source manifest，在最终产品`0a6de39`、交付`c69018d`及当前工作区三处均相符；产品提交之后23个变更路径全部为文档。最终3.10受影响120项（含新增47项）、新构建/干净安装/pip check/安装来源及关键smoke采用已核验身份的执行记录与[独立补修review](W005/ipmr01-fix-review.md)。补修原wheel不在本PM环境；67项wheel/安装文件一致性采用该独立review的实际核验，不以本机旧wheel代替，也不声称本轮重新构建或安装。

3.10本轮未重跑全套或干净安装的边界与PM2受影响回归要求一致，不构成新增补修阻塞；其他平台/解释器及真实工具仍未验证。本轮仅记录技术接收，未合并main或启动下一产品任务。建议下一步完成W005合并与实际集成核验，再准备输入组件接入正式运行审计的近期任务；无需重开完整组件review。pipeline、Stage2、Stage6与完整M1义务仍按后续组合表保留。

### 历史派发背景（2026-10-31至2026-11-02）

以下保留原派发事实；当前状态以PM3及任务顶部为准，不从旧prompt重新执行。

W003/W004样本前置及REQ-01补修已通过PR #58合入main `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，集成事实见[W004 PM6](W004-fixture-revision.md#pm6-20261102)。当前派发W005读取组件，不代表W005实现或M1完成。按用户选择，新独立执行session从`codex/w005-input-reading-binding`的PM交接提交恢复，准确SHA见Git/回复；本轮只更新交接，不提前编写执行者方案或产品代码。

**派发文档复核（2026-10-31，PM记录）：**未参与本任务编写的`body_scope`对照架构完成独立复核，剩余必须修正项为0。已落实其body内部引用/Stage2定位分界、header运行与匹配状态组合校验等意见，并明确C09语义准入及图形/stream record区别。受审全文SHA-256为`bd5330364c3107e569841b3271ec3adab23029ab6a6eb427c5bfe586bb7dec62`，覆盖追加本段之前的任务正文。`pm_review`另复核收口/导航/portable receipt，旧阶段冲突已修正，无剩余必须修正项。两项均为文档复核，不表示产品代码或测试已经通过。

### 历史执行session prompt（实现已交付，不重复执行）

```text
按Layauto项目规范，以执行角色完成W005输入读取与绑定组件。
从codex/w005-input-reading-binding的PM交接提交恢复，先核对HEAD、已包含main集成87fe5a5a87d0cbb1f97952f1485dac9a71416369及全部已有差异；读AGENTS、README、协作规则、current-work、W005及引用的架构/已验收W004输入合同。
W003/W004已合入main，REQ-01已修复，不重做样本修订或照搬helper为产品代码。按W005补简短API/DTO/错误边界方案，安排独立接口review后直接实现；普通内部选择自主处理，不在接口方案完成后无故停止。
真正从GDS/CDL/raw/header/config/context读取并校验，不从expected/oracle/spec或normalized-only加载答案；完成A1–A7及跨样本变体验证。
本任务仅组件API。pipeline/run入口、RunAttempt/RunRecord终态、Stage2状态与Stage6导出按W005后续组合表保留，不虚报本次已完成；新关键行为变化附实例交PM。
代码完成后安排未参与实现者独立review，修复必须修正项并复核，交完整版本/命令/结果/未执行范围。保留历史MR/E/R和已验收fixture。
完成后将本任务实现、测试、执行/review记录提交推送到codex/w005-input-reading-binding，并核对远端SHA，便于PM跨环境接收。交回实际命令、结果、未验证项及可访问证据；不自行最终验收W005、合并main、删分支或扩展到下一产品任务。
```
