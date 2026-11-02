# W005 — 读取真实文件并核对输入绑定

把已验收的样本交给正式v2读取组件：从GDS、source/target CDL、raw query与配置读出可追溯的内容；文件缺失、格式不支持或来源不一致时给出明确错误。成功输出可供后续Stage 2消费的evidence，不从样张加载预制状态。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| 目标 / 依赖 | M1的首个产品组件切片；依赖已验收的W003/W004样本，实物基准`633e3feef8062565019838f2d270e89b7f81c4ed`。W002 E7的完整no_change闭环目标及R4首交义务保持 |
| 授权 / 阶段 | 2026-10-31用户同意准备读取任务；2026-11-02选择合并W004后由独立执行session继续，并由PM准备新分支与prompt。**可执行：下一执行session按本任务实现读取/绑定组件；本PM session仅准备交接，产品代码未开始。** 无当前输入语义待决项 |
| 恢复版本 | 执行分支`codex/w005-input-reading-binding`，从main集成提交`87fe5a5a87d0cbb1f97952f1485dac9a71416369`建立，已含W004及REQ-01修复；使用包含本轮PM交接的提交，准确SHA见Git/回复。主样本仍为633e3fe的原bytes，不从旧W004分支另起实现 |
| 输出边界 | 一个可由测试及未来pipeline调用的组件API，返回不可变、经过运行时校验的配置/tech及versioned evidence、解析结果和定位信息。名称/DTO组织由执行者细化并review；本轮不发布新的稳定CLI或对外wire承诺 |
| 允许修改 | `layauto_v2/importers/`，必要的中立`domain/` evidence/results/codec类型、`tech/` schema与纯读取公共入口；`tests/unit/`、`tests/contracts/`及读取组合测试；必要依赖/typing/build配置与使用说明、本任务执行记录。新增目录按职责创建，不为所有未来模块填空 |
| 非目标 | 不实现pipeline/run入口、repository/RunAttempt/terminal publication、Stage 2 identity/spatial join与状态、规则求值/resize/导出、真实Calibre/Virtuoso获取或生产上传；不改变D1=A、MR-040后置及真实工具延期。不修改已验收fixture以迎合程序 |
| 架构依据 | [architecture](../architecture.md) §2.1–2.3、§3.1–3.2、§4.8、§5、§11.2/11.10/11.13–11.15、§12.1–12.8；架构原文优先，任务不另定产品合同 |
| 分工 / 阻塞 | 一名执行者统一集成；未参与实现者做接口/最终代码review，PM核对结果。当前无阻塞；普通内部选择自主处理，新关键输入/能力/对外行为变化附实例交PM |

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


## Review 结论（reviewer）

### R1. 独立接口与最终代码复核（2026-11-02，reviewer）

`interface_review` 对 E1 方案独立复核后允许进入实现，记录见 [接口review](W005/interface-review.md)。未参与产品实现或测试编写的 `final_review` 另对 base `5b7205009b3ed7f8fe15e135e674654f2f544557` 至最终实现 `ab7feddff83749b54c1866b1ad95fbc99fd787f1` 完成代码、实际输入、错误路径与 A1–A7 证据复核；[完整报告](W005/code-review.md)保留五项原始 finding、修复及独立关闭依据。**无剩余必须修正项，交 PM 接收；不代替 W005 最终验收。**

Reviewer 直接运行最终 Python3.12 完整组件测试 **237 passed**、strict mypy **13 source files**，并在 Python3.10 复跑10项相关修复回归。已对照执行者最终3.10完整237项、构建安装日志和22文件manifest；独立核验最终wheel与受审产品文件相同，并从源码目录外以安装环境`-I`运行正常及重绑坏raw读取。原fixture/答案/support/架构/current-work未改写。pipeline、Stage2状态/物理匹配、Stage6导出及真实工具/生产验证仍按任务边界后置，读取成功不等于其准入通过。

## PM 验收与交接（PM）

W003/W004样本前置及REQ-01补修已通过PR #58合入main `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，集成事实见[W004 PM6](W004-fixture-revision.md#pm6-20261102)。当前派发W005读取组件，不代表W005实现或M1完成。按用户选择，新独立执行session从`codex/w005-input-reading-binding`的PM交接提交恢复，准确SHA见Git/回复；本轮只更新交接，不提前编写执行者方案或产品代码。

**派发文档复核（2026-10-31，PM记录）：**未参与本任务编写的`body_scope`对照架构完成独立复核，剩余必须修正项为0。已落实其body内部引用/Stage2定位分界、header运行与匹配状态组合校验等意见，并明确C09语义准入及图形/stream record区别。受审全文SHA-256为`bd5330364c3107e569841b3271ec3adab23029ab6a6eb427c5bfe586bb7dec62`，覆盖追加本段之前的任务正文。`pm_review`另复核收口/导航/portable receipt，旧阶段冲突已修正，无剩余必须修正项。两项均为文档复核，不表示产品代码或测试已经通过。

### 下一执行session prompt

```text
按Layauto项目规范，以执行角色完成W005输入读取与绑定组件。
从codex/w005-input-reading-binding的PM交接提交恢复，先核对HEAD、已包含main集成87fe5a5a87d0cbb1f97952f1485dac9a71416369及全部已有差异；读AGENTS、README、协作规则、current-work、W005及引用的架构/已验收W004输入合同。
W003/W004已合入main，REQ-01已修复，不重做样本修订或照搬helper为产品代码。按W005补简短API/DTO/错误边界方案，安排独立接口review后直接实现；普通内部选择自主处理，不在接口方案完成后无故停止。
真正从GDS/CDL/raw/header/config/context读取并校验，不从expected/oracle/spec或normalized-only加载答案；完成A1–A7及跨样本变体验证。
本任务仅组件API。pipeline/run入口、RunAttempt/RunRecord终态、Stage2状态与Stage6导出按W005后续组合表保留，不虚报本次已完成；新关键行为变化附实例交PM。
代码完成后安排未参与实现者独立review，修复必须修正项并复核，交完整版本/命令/结果/未执行范围。保留历史MR/E/R和已验收fixture。
完成后将本任务实现、测试、执行/review记录提交推送到codex/w005-input-reading-binding，并核对远端SHA，便于PM跨环境接收。交回实际命令、结果、未验证项及可访问证据；不自行最终验收W005、合并main、删分支或扩展到下一产品任务。
```
