# W009 独立代码 review

- 日期：2026-11-03；reviewer `/root/code_review`，未参与方案设计或产品实现。独立数学专项 `/root/code_review/math_probe`。
- 仓库/分支：`LucianoHoult/Layauto` / `codex/w009-effective-geometry-terminals`；起点 HEAD `4975e565a33d9594782645b6ad0f944b78ee6ae8`。
- 审阅范围：新增 domain/state regions、normalization effective/result/codec、对应 tests/helper；README、公开导出、typing 配置及纯依赖边界白名单；任务执行记录和最终验证证据。
- 当前判断：**代码和最终工程证据审查完成；CR-01/CR-02均已独立复核关闭，剩余必须修正项0，可交PM核验接收。** 这不是 PM 验收或合并决定。

## Finding 原文、修正与复核

| ID | 必须修正项与影响 | 执行处置及 reviewer 复核 |
| --- | --- | --- |
| CR-01 | `normalization/effective_codec.py::_unpack` 对所有 neutral constructor 包裹 `except(TypeError, KeyError, AttributeError, IndexError, UnicodeError)`，把 aggregate 重建中真正的内部算法错误翻译成畸形 wire 的 ValueError。独立复现：正常 W005→W008→W009 草稿编码后，将 `state.regions.slab_difference` 临时替换为抛出一个 TypeError 实例的函数；`decode_record(draft_wire)` 得到 `ValueError("invalid effective geometry wire fields")`，`same_object=False`，原异常仅留在 cause。外层成功结果的嵌套草稿同样受影响。违反任务行为6/A6 的意外异常同对象传播；原测试只覆盖 builder 和 captured decoder，未覆盖 neutral aggregate decode。 | 执行者移除 broad constructor 翻译，由 closed wire tags 和 typed constructor 显式检查结构；`OperatorBinding` 对缺失 layer/name/role 改为明确结构检查。新增 draft/result 各8种算法异常 identity 回归。Reviewer 重新读取实际修正，并用独立 [exception probe](review/exception_probe.py) 在 3.12、3.10 各执行 draft/result×9种异常，共各18例，全部同对象传播；包括 UnicodeError、KeyboardInterrupt、SystemExit。**关闭**。原 [codec 文本](review/effective_codec-before.py.txt) SHA-256 `77a2446cc924cdab31d328c9a1f78a7dfee4336154a0c9a02f0cc4711bcd5d18`、[初始工具观测](review/exception-initial.txt)及[修后3.12](review/exception-after312.json)/[3.10](review/exception-after310.json)保留。 |
| CR-02 | 新 DTO 的 Literal/schema 字段只做值比较或 tuple membership，没有先检查确切 str 类型。独立构造一个可变 `MutableLiteral`（`__eq__` 恒 True、`__ne__` 恒 False）：`RegionRef(literal, 'a'*64)` 被接受；把正常 `ExactRegion.role` 替换成该对象，再逐层 replace RecordRegions→EffectiveDraft→成功 Result，均被接受；随后 caller 向 `literal.items` append 即改变成功结果内同一 alias。该对象不能编码 wire，但公有 constructor 已违反 closed/递归不可变合同。涉及 domain `_version`、RegionRef.kind、ExactRegion.role、RecordRegions.operation 及 effective result schema/status 的同类入口；不要求本轮扩修历史W008。独立 [probe](review/literal_alias_probe.py)，受审 domain/effective 源码见 [domain原文](review/regions-before-cr02.py.txt)/[result原文](review/effective-before-cr02.py.txt)。 | 已显式检查 native str/schema/unit literal，并对原生容器先复制后校验；对旧base集合严格检查实际DTO类型。最终增加统一 `validate_closed_graph`：在任何编码/折叠前检查完整原对象图，只允许 identity 比较的原生Value、内部n/d也是native int的exact Fraction、原生FrozenMap/tuple及调用方固定known DTO classes；payload只允许Value代数。owner/base/完整input/completed/issues均走该检查，旧codec/DTO未改。Reviewer 独立复核全部分支和公开字段接缝，并运行下列具体反例，均已拒绝或保持安全快照。**关闭**。 |

### CR-02 的完整根因与闭合范围

初次 literal 反例后，对同一“保留原对象而只校验相等/编码值”的根因继续核对，复现了：旧receipt/base/fragment的字符串子类、completed/issue/owner metadata；容器两次迭代分别返回真DTO和等值Foreign DTO；metaclass伪造type相等使旧codec仍保留str子类；exact Fraction内部保留有可变属性的int子类。编码值可以相同，不能替代对原对象图的检查。最终统一检查以类型身份白名单关闭这些入口；没有通过修改旧W008合同或扩大生产输入语义解决。

具体可重建见证与版本：

- [最初literal阳性结果](review/literal-alias-before.json)，对应保存的旧domain/result文本和[旧240项清单](review/pre-cr02-source-manifest.json)；修后[literal 3.12](review/literal-alias-after312.json)/[3.10](review/literal-alias-after310.json)拒绝。
- [borrowed alias probe](review/borrowed_alias_probe.py)的6类receipt×两公开入口，加base两类×两state入口及owner/completed metadata，共各24项；[3.12](review/borrowed-alias-after312.json)/[3.10](review/borrowed-alias-after310.json)均拒绝。
- [container probe](review/container_alias_probe.py)在完整[9899源码zip](review/pre-container-source.zip)中重跑，8条路径原来均成功保留可变Foreign DTO；[原结果](review/container-alias-before.json)保留实际snapshot import路径。修后[3.12](review/container-alias-after312.json)/[3.10](review/container-alias-after310.json)全部闭合。zip包含240文件和manifest；SHA-256 `ddb83fde7605ed6991b5fadf86f029c547d1d8fbdd69fe08bab69cdd7b0f1a0b`。
- 独立专项 `/root/closed_value_audit` 及其legacy graph专项进一步复现的[metaclass原脚本](review/metaclass_probe.py)/[原结果](review/metaclass-before.json)、[Fraction原脚本](review/fraction_atom_probe.py)/[原结果](review/fraction-atom-before.json)保留。Reviewer 在最终统一检查上直接重跑：metaclass [3.12](review/metaclass-after312.json)/[3.10](review/metaclass-after310.json)均定位到新closed graph检查拒绝；Fraction [3.12](review/fraction-atom-after312.json)/[3.10](review/fraction-atom-after310.json)均拒绝。单独旧freeze仍可接受这些类型，本轮只在W009边界隔离。

独立43项literal/borrowed/metadata定向回归在3.12 **43 passed / 36.98s**、3.10 **43 passed / 39.28s**（[输出](review/cr02-targeted312.txt)、[输出](review/cr02-targeted310.txt)）。这些记录是各修正阶段的直接运行事实；最终全量矩阵另行绑定最终source manifest，不把修前或中间结果冒充最终版本。

最终统一检查冻结后，Reviewer在两解释器重新执行全部67项CR-02 literal/borrowed/container/metaclass/Fraction/known-record回归：3.12 **67 passed / 18.38s**、3.10 **67 passed / 20.49s**（[最终3.12](review/cr02-final312.txt)、[最终3.10](review/cr02-final310.txt)）。数学probe也在最终源码重新执行；[probe身份审计](review/final-probe-identity-audit.json)确认最终数学、container/metaclass/Fraction双解释器结果里的所有源码SHA均等于最终32e60e783清单条目，旧数学结果另存历史文件。

## A1–A8 技术判断

| 要求 | 独立审阅结论 |
| --- | --- |
| A1 输入与来源 | 公开入口只接受成功 W008 GeometryResult；完整 input receipt 进入外层结果与 wire。physical evidence 的 payload 和 source role 来自同一 W008 捕获；success 对完整 base/physical 再核验。W008 codec 对嵌套 input 重走捕获认证，成组 downstream payload 不能替换原字节。W006 readback 与原语义/query/body/attempt 保留；新 builder 无文件/repository IO。 |
| A2 支持子集 | 消费字段逐项核验 profile/operator 版本和完整声明语义；先定位 OD/POLY/LI/CUT，再检查四个角色和 CUT 目标/operator。未消费 required operators 只保留其证据，未宣称其执行完成；未知/矛盾已消费语义定位拒绝。 |
| A3 精确差集 | integer slab subtraction 保留全部正面积余量，重复/重叠 CUT 按集合覆盖而所有命中原 record 来源保留。规范分解没有 bbox 填洞，空差集仍有 record result；局部正长度边分组不会把角触片合并。独立数学探针另见下节，未发现漏片或额外覆盖。 |
| A4 沟道与端区 | 正面积 OD∩POLY 才能识别 channel。完全重合 stripe 保留每条来源，不同几何 stripe 同时命中拒绝；full-y 与 interior-x 条件对当前矩形 toy 合同恰好保证完整左S/右D及互斥还原。没有按正常数量、query/CDL 名或原 record 序号硬编码，也没有 S↔D 导体边。 |
| A5 special | 测试从原 special GDS 经临时 header/body/query top 重绑读取；LB 两块 [130,20,139,24]、[141,20,150,24]、面积72及 A_REMOTE 保留只作几何判据；未挪用其 component/spacing/规则答案。原 fixture 未修改。 |
| A6 公共合同 | closed/versioned typed refs 与 canonical wire；region 本地检查排序、互斥、canonical cover和内部连通，父 EffectiveDraft 根据完整 base/owner 重建全部 record regions，拒绝遗漏/多片/外来来源/单位/算子及填洞。新字段均为 immutable DTO或复制后的 tuple，无可写 caller alias。neutral binding 与最终捕获认证分层明确。CR-01 已补齐算法异常的 decode 边界。 |
| A7 范围 | 原 raw geometry/base occupancy/body/semantic/query 经原 receipt 保留；region/piece refs 可供后续消费者引用。没有电气 ComponentId、net stamp、connector edge、FIN/body证明、query overlay、baseline/terminal 或完整坐标准入声明；U06 和其他后续义务在执行交接中明确保留。 |
| A8 工程 | typing 配置和精确依赖白名单与实际纯组件责任一致。最终双解释器各914项、各44模块typing和15项命令/输出身份已核验；两包/两实际安装各90项runtime与最终源相同。完整矩阵采用执行者实际回执，reviewer没有冒称重跑全矩阵。 |

## 独立数学与复跑

[数学 probe](review/math_probe.py) 不使用执行测试 helper 作 oracle：以整数化边界/中点逐点判断 target-minus-union-cuts，以单元格四邻接 BFS 独立求局部分组，另比较冗余分解/重复/重排的 canonical cover。最终源码上 **1,515组集合、585,511个点归属检查、1,505组独立BFS分组、1,515组冗余分解** 通过，包含孔洞、角触、全覆盖及 ±2**80 平移；[结果及源码SHA](review/math-result.json)。这证明有限见证，不是生产规模性能保证。

另外以 [scalar probe](review/malformed_scalar_probe.py) 将七类公开合同的每个字段替换成四种不相容 scalar，**132项均明确以 ValueError 拒绝**，没有用 broad 异常翻译掩盖算法错误；[原始结果](review/malformed-scalar-results.json)。

Reviewer 直接执行（以下117/8项及132项为CR-02之前的审阅阶段；后续修正的直接复核见上节，最终全量证据另见末节）：

| 环境 / 命令 | 结果 |
| --- | --- |
| `/workspace/work/w009-env/py312/bin/python -m pytest tests/contracts/test_w009_contracts.py tests/contracts/test_w009_effective.py -q` | **117 passed / 201.90s**；[原输出](review/targeted312.txt) |
| `/workspace/work/w009-env/py310/bin/python -m pytest tests/contracts/test_w009_contracts.py -q -k 'neutral_reconstruction or malformed or grouped or nested_result or result_discriminators'` | **8 passed, 55 deselected / 43.33s**；[原输出](review/targeted310.txt)。这是定向选择，不冒称运行完整3.10新增集或16项新回归。 |
| 两解释器分别运行 `python docs/tasks/W009/review/exception_probe.py` | 各18项全部同对象；结果绑定4个相关源码SHA。 |
| 3.12 `python docs/tasks/W009/review/math_probe.py` | 上述1,515组与585,511点通过；结果绑定domain/state源码SHA。 |
| 3.12 malformed scalar probe | 上述132项明确拒绝。 |

[初次源码身份审计](review/source-identity-pre-cr02-audit.json)重算CR-02之前清单全部 **240文件**，零差异；manifest SHA-256 `9e3fde92ea6919e70592a7b71d03c575e8e81471d7ca835829052277a8208957`。最终清单核验见末节。受审内容覆盖 staged/unstaged/untracked 的相关源码、测试、配置与README；不能只用尚未提交的 HEAD 代表这组新增材料。

资源审阅确认最终执行文档计入 slab O(m² log m)、可能 O(m²)输出片数、分组 O(p²)，以及 region 的 pairwise overlap/connectedness O(p²)与 canonical_cover O(p² log p)自校验。没有新增外部规模上限；完整链还包括 W008/base 重建和 codec 捕获认证。

本轮没有修改产品/测试/fixture、PM段或 current-work，也没有提交/推送。Review 附件保留直接执行与采用执行者证据的区别。完整工艺坐标、region occupancy投影、contact/connectivity、器件/标注/body证明、baseline/seal/no_change/Stage6及真实EDA/PDK验证仍在任务范围之外。

## 最终身份与工程证据

最终source manifest SHA-256 `32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`，240项源码/测试/配置与README由reviewer实际重算匹配。[独立package audit](review/package_audit.py)/[原结果](review/package-audit.json)核对当前wheel/sdist及两套实际安装目录各90项runtime字节，全等于最终源；同时核验pip install-report的直接artifact URL和hash、实际安装路径、两次smoke的真实cwd、`-I -B`及site-packages来源、原始输出hash与成功检查。两次smoke的实际cwd均为`/workspace/work/w009-env/installed-cwd`，在checkout之外。Reviewer未重新构建或重装两包；这是对执行者产物和实际安装树的独立字节/来源核验。

- wheel SHA-256：`27e97b27f8e3a4f5e2ff804a32fe3bd3aa33d3a6ea1f3e9b96075ea5858aaf95`。
- sdist SHA-256：`2716df4fe382dfb64127ed9b46ee3c80aa53b071bab10175d7e4b65806c72c98`。

[最终evidence audit](review/evidence_audit.py)/[原结果](review/final-evidence-audit.json)实际核验最终receipt的全部15项命令均exit0、原始输出SHA全部匹配；Python3.12.14 **914 passed / 1053.71s**、Python3.10.22 **914 passed / 1502.45s**，两次strict mypy各**44模块**通过，dev/安装环境pip check、build及两次源码外smoke通过。914项包括保留原730项和新增184项。Reviewer采用已独立核验的执行者完整矩阵/构建回执，直接运行范围已在上文分阶段列明。

[归档及证据manifest审计](review/final-archive-evidence-audit.json)另实际读取完整源码tar的240项并与最终manifest逐字节比较，零差异；核验verification证据manifest中全部117个文件hash。完整源码tar SHA-256 `5ed2228559ea6dcf7a1417e19b8f706f1e88283edfca0c01809489cb147ec727`，最终receipt SHA-256 `d16180c0dc13bc9ce15459ec8735857dda52e2379b99d8b5f1564dd02704cf66`，证据manifest SHA-256 `e421a6be4e341ed3ddf907f1f5e9617db7ca2f517b94b14a6b226a89dc4072c7`。终场source manifest仍为上述32e60e783，当前240源项再次核对零差异。

最终数学/closed probes的源码身份由[专门审计](review/final-probe-identity-audit.json)核对；有限性能见证的10条命令均绑定最终三文件SHA，区分实际capture、neutral stress和纯差集，含公开API严格原图/重复编码检查成本。没有把有限规模当生产性能保证。本段不采用pre-cr02/pre-container的旧包、中止矩阵或旧安装作为最终通过。

据上述实际源码、独立反例修正复核、有限数学判据、最终矩阵和可访问产物，**A1–A8在本任务声明的synthetic/toy范围内已有可核验交付依据；建议PM进入验收核验，剩余必须修正项0。** 本结论不是PM验收、main集成或完整Stage2/M1/生产准入结论。
