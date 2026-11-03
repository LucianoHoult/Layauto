# W009 独立合并前复核

日期：2026-11-03。Reviewer：本 session `/root`，未参与原 W009 方案、实现或 PM 接收；本次并行专项仅向本 reviewer 提供独立检查材料。

**结论：剩余必须修正项 1（P2，IPMR-01），暂不建议 PM 进入集成。** CUT/channel/空间 S/D 数学、来源绑定、原对象图与交付身份已有独立核查依据；A6 的完整嵌套 decode 异常合同仍有缺口。保留原 IR-01、CR-01、CR-02 和 PM1 原文；本报告追加新的判断，不改写历史关闭记录或 PM 阶段。应先按原合同修正 IPMR-01，再独立复核受影响路径及交付身份，交回 PM 决定集成。

## 实际受审版本与范围

| 角色 | 完整 SHA |
| --- | --- |
| main 基线 | `4df07e68b05df4c57a8b8d44bc41e7e073938d3a` |
| W009 准备 | `4975e565a33d9594782645b6ad0f944b78ee6ae8` |
| 产品交付 | `5b1d9b5196a7c5181822c4dd0f1bd2f678475116` |
| 本次待审 HEAD | `88a7ae9d0330b7c7fddda0b07366c7a96552b65e` |

初始 `/workspace/Layauto` 为 `work@4df07e68…`，origin 为 `https://github.com/LucianoHoult/Layauto.git`，staged/unstaged/untracked 全空。实际 Git 远端查询和 GitHub ref 查询确认 W009 为指定待审 HEAD、main 为指定基线，未发生远端漂移。默认命令沙箱不能连接代理，采用平台附加网络权限完成 Git 查询/fetch，保留代理与 TLS。另建 `/workspace/work/w009-review` worktree，分支为 `codex/w009-effective-geometry-terminals`；原 checkout 保持不动。

审查 **main→待审 HEAD 的完整交付**，以 **准备→产品** 定位四个新增产品模块、公开导出、typing 配置、两份新合同测试/输入 helper，以及 W007 纯依赖测试的精确例外。产品→待审 HEAD 仅 PM 文档、导航及证据，不能代替实现审查。[版本与路径记录](independent-premerge-review/version-scope.json)/[可复验脚本](independent-premerge-review/version_scope.py)保存三段提交链、完整路径、实现文件 hash 及保护路径零差异。fixture/答案、架构和 W003–W008 历史材料相对准备提交未改。

已依次读取根 AGENTS/README、协作及本地/远端环境说明、W009 任务、plan/plan-review、execution/code-review、pm-receipt.md/json；再核对所引架构 §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§11.2–11.3/11.14–11.15、§12.3/12.5、W008 输入/单位/逐 record/base occupancy 合同及接口、W003 contracts 和 MR-045/046、MR-052/054/056。无后代 AGENTS。恢复以 PM1 为准：W004 修订后的外部 body context 是当前 synthetic 合同；旧本地 BTAP、旧派发和中间验证快照各保留原版本含义。

## A1–A8 判断

| 要求 | 本次独立判断 |
| --- | --- |
| A1 真实组合与来源 | 满足所审子集。实跑真实 W005 和 W006 readback→W008→W009，禁文件/repository IO后仍等价；同一 captured physical/drawn/formats 来源、单位及完整 input 保留。wrong-run、错 owner、成组 value/completed 及 nested wire 伪造拒绝；原语义/query/body/base/attempt 不改。 |
| A2 算子与作用域 | 满足。先唯一定位 OD/POLY/LI/CUT，再核对 diffusion/gate/interconnect/cut，CUT target=LI、差集版本及 physical profile/channel/S-D 语义逐字段校验。真实修改捕获并重绑的反例定位拒绝；未把未消费算子名字/能力声明当执行成功。IR-01 的实现关闭有效。 |
| A3 差集数学 | 满足本次有限判据。独立 pixel 集合、点归属、互斥及四邻接分组覆盖孔洞、多片、全空、未命中、边角触、重复/重叠 CUT、负值、大整数、重排。重复原 record 和全部贡献 CUT 来源保留。未用同产品算法提供 expected。 |
| A4 channel/端区 | 满足当前 toy profile。正常两 channel/四端区与手写 bounds 相符；无 gate、多 stripe、部分交叉、边角触、贴边/横向/全覆盖拒绝；相同几何重复 POLY 保留全部来源。channel/S/D 互斥并完整还原每个适用 active，不依赖展示名、record 序号或正常数量。 |
| A5 special | 满足。实际 special/cut_islands 经临时捕获重绑得到 LI `[130,20,139,24]`、`[141,20,150,24]`，面积 72；A_REMOTE `[50,20,60,24]` 保留。没有沿用其 component/spacing/body/规则终态答案作本轮成功声明。 |
| A6 公共合同 | **未完全满足：IPMR-01。** 聚合重建、closed wire、内容 refs 与 canonical 约束有依据；CR-02 原对象图关闭有效。但 draft/result 内复用的 W008 base decoder 仍翻译内部意外异常，原 CR-01 关闭证据只覆盖部分完整调用链。 |
| A7 范围与后续 | 满足。raw drawn/base occupancy、W007 语义/query及独立 body 证据仍保留；无电气边、canonical device/net join、FIN/body 提取、完整工艺网格或整轮成功宣称。U06 与 synthetic body_context 必填均未改变。 |
| A8 工程/身份 | 本次完整 v2 **914 passed / 1010.02s**，strict typing **44模块通过**。最终源码、快照、包实物、归档输出及修正证据身份匹配。历史双解释器、构建与两套干净安装按身份核验后采信；本机没有旧安装树。性能说明披露片数增长、后处理与完整认证成本，无新增外部限制或生产性能保证。 |

## 必须修正项

### IPMR-01 — P2：W009 嵌套 base 解码仍改写内部异常对象

位置：[effective_codec.py:67](../../../layauto_v2/normalization/effective_codec.py#L67) 的 `geometry_record` 分支（调用在第71行）委托旧 [geometry_codec.py:107](../../../layauto_v2/normalization/geometry_codec.py#L107)；后者第109–110行仍以 `except (TypeError, KeyError, AttributeError, IndexError, UnicodeError)` 包裹 neutral constructor。旧文件未在 W009 diff 中改动，但新增 W009 draft/result 的公开 decode 会经过此分支，因此问题在本次组合边界可观察。

**最小复现：** 从实际正常输入构建 W005→W008→W009，先正常编码 `result.value`；随后仅在内存临时将 `state.occupancy._fragments` 替换为抛出既有 `TypeError` 实例 `failure` 的函数，再调用 `effective_codec.decode_record(draft_wire)`。无需篡改 wire、fixture 或源码。[主 reviewer 独立脚本](independent-premerge-review/validation/nested_base_confirmation.py)及[实际结果](independent-premerge-review/validation/nested-base-confirmation.json)保存 HEAD、wire hash、源码 hash 和原始观察。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" python -B \
  docs/tasks/W009/independent-premerge-review/validation/nested_base_confirmation.py
```

脚本退出 0 表示成功复现缺陷，JSON 明确记为 `contract failed`。

| 项目 | 预期 | 实际 |
| --- | --- | --- |
| 合法 W009 wire 内部 base 重建出现意外算法异常 | 原 `failure` 同一对象向外传播 | `ValueError('invalid geometry wire fields')`；`observed is failure` 为 False，`observed.__cause__ is failure` 为 True |
| 完整 draft/result 异常路径 | 每个层次保持同一异常对象 | 99项矩阵中69项保持原对象、30项被替换；失败恰为两个入口×三类 base 算法×五类 catch。见[原始输出](independent-premerge-review/provenance-exceptions/exception-paths.json)及[专项报告](independent-premerge-review/provenance-exceptions/report.md) |

影响：真实 base layout/partition/occupancy 重建中的算法或基础设施错误会被误分类为畸形外部 wire，破坏调用者对组件错误的区分及原异常对象身份。保留 cause 不能满足 W009 行为6/A6 和本轮明确的 CR-01 条件。正常结果数学正确和现有回归通过也不能关闭该错误路径。`KeyboardInterrupt/SystemExit` 仍正确传播，本 finding 不声称中断被吞或正常几何错误。

修复建议：使 **W009 完整嵌套 decode 调用链** 对内部意外 Exception 保持同对象传播；畸形结构由显式字段/类型/constructor 校验明确拒绝。可修正复用 decoder 的异常边界，或提供等价且安全的组合方式；不要 broad catch 后凭异常类型猜算法/输入错误，也不要通过只保留 cause 或放宽验收消除此项。补充 draft/result×layout/partition/occupancy 的内部异常回归及 malformed wire 对照，再核对受影响旧回归、最终证据和包身份。该建议不要求无关历史模块全面重写。

## 本次实跑与独立证据

本次环境：Linux、Python 3.12.14，既有 `/workspace/.venvs/layauto`；pytest 9.2.0、PyYAML 6.0.3。mypy 2.4.1/types-PyYAML 安装在独立 `/workspace/work/w009-premerge-deps`，不改依赖声明或原环境。[环境观察](independent-premerge-review/validation/environment.json)记录实际导入路径与依赖，并说明 pytest wrapper 自身未带 task 依赖路径、故其 mypy/stub 元数据为 null，而实际子命令使用所记 PYTHONPATH override 的区别。所有产品检查禁字节码；pytest 禁缓存，其本次临时根为独立运行目录 `/tmp/pytest-of-agent/pytest-0`；mypy/pip/绘图缓存及临时 captures 位于 `/workspace/work` 下独立目录。命令、真实 cwd/HEAD、环境、耗时、退出码和原始输出 hash 由[runner](independent-premerge-review/run_check.py)及 `validation/` 保存。

| 本次实际执行 | 结果/材料 |
| --- | --- |
| `python -m pytest tests/unit tests/contracts -q -p no:cacheprovider` | exit 0，**914 passed in 1010.02s**，stderr空、无warning；[完整输出](independent-premerge-review/validation/pytest.stdout.txt)/[回执](independent-premerge-review/validation/pytest.json)。wrapper总耗时1013.031s |
| `python -m mypy --cache-dir /workspace/work/w009-premerge-cache/mypy` | exit 0，**44 source files**；[输出](independent-premerge-review/validation/typing.stdout.txt)/[回执](independent-premerge-review/validation/typing.json) |
| `python -m pip check` | exit 0；[回执](independent-premerge-review/validation/pip-check.json) |
| 独立几何 probe | **4,418 组 / 521,222 点**及真实 normal/special/12 gate/重复来源组合通过；[报告](independent-premerge-review/geometry/report.md)、[脚本](independent-premerge-review/geometry/probe.py)、[结果](independent-premerge-review/geometry/result.json) |
| 原对象图 probe | 七类 constructor/decode，正常结果 **5,488** 个不同非原子对象；**31** 反例拒绝，**7** list 快照保持；[报告](independent-premerge-review/object-graph/report.md)/[脚本](independent-premerge-review/object-graph/probe.py)/[结果](independent-premerge-review/object-graph/result.json) |
| 来源与异常路径 probe | 来源/真实组合/拒绝共**26项通过**（含8项畸形wire）；异常矩阵**99项、30项失败**即IPMR-01。见[专项报告](independent-premerge-review/provenance-exceptions/report.md)、[来源结果](independent-premerge-review/provenance-exceptions/provenance-results.json)、[异常矩阵](independent-premerge-review/provenance-exceptions/exception-paths.json)。主 reviewer 另行最小复现 |
| 独立只读身份审计 | 240 源项、完整 tar、117 证据、15 命令输出、两包各90 runtime、20 PM附件及最终修正/性能 SHA 均匹配；[报告](independent-premerge-review/evidence/report.md)/[脚本](independent-premerge-review/evidence/audit.py)/[结果](independent-premerge-review/evidence/result.json) |

数学 probe 用独立集合/四邻接和精确点归属判据；产品函数仅为被测对象，未用面积相等或再次调用同一算法代替 oracle。真实 LI 孔洞见证还核对 W008 raw axes 未含 CUT 内边界、原 cell/fragment 仍完整，W009 差集正确；内部矩形分解没有升级为工艺网格。对象图 probe 在 codec 折叠前独立遍历真实保留对象（包括 FrozenMap backing），新增有副作用的类型/迭代陷阱和 `__class__` 身份伪装；完整回归还覆盖原 metaclass/Fraction/容器等根因。对 frozen DTO 私有存储的强制绕过不作为正常公有入口反例。

## 采信证据、建议与未验证范围

最终 source manifest SHA-256 `32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`，240 项当前文件与产品/待审 Git 对象逐字节一致；完整 tar SHA-256 `5ed2228559ea6dcf7a1417e19b8f706f1e88283edfca0c01809489cb147ec727`。wheel `27e97b27f8e3a4f5e2ff804a32fe3bd3aa33d3a6ea1f3e9b96075ea5858aaf95`、sdist `2716df4fe382dfb64127ed9b46ee3c80aa53b071bab10175d7e4b65806c72c98` 的各90项 runtime 与最终源一致。

原 Python3.10.22/3.12.14 各914项、各44模块 typing、构建、两套干净安装和 checkout 外 `-I -B` 真实组合 smoke，按原最终回执、可访问包实物及原独立审计采信。本机原安装树不存在；**未重建、重装、遍历原安装树或重跑3.10，没有把日志/hash一致写成重新安装或重新观察历史执行。** 中间 pre-cr02/pre-container 的快照、旧包和中止矩阵各按原身份保留，不作最终通过依据。原 CR-01 probe 和 PM 复跑确实在其所测路径保持异常身份，但没有覆盖本次发现的嵌套 base 算法路径。

非阻塞建议：后续真实规模验证补充高片数、多孔单 region、共享捕获反复认证的规模曲线和内存峰值；当前 O(m² log m) 差集、O(m²) 片数及 O(p²)/canonical cover 后处理和重复验证成本的披露诚实，有限性能记录不构成生产保证，不新增本轮门槛。单独 neutral `RecordRegions` 的局部重复/排序可考虑加强或明确用途；完整 `EffectiveDraft` 会拒绝重复区域，当前未据此认定伪造 success 或新增必须修正项。

完整工艺坐标/合法空间、有效区域 occupancy 投影、物理接触/连接图、标注、canonical device/net join、FIN/body 提取、规则、baseline/seal/no_change、Stage6 与真实 EDA/PDK 均未由本轮完成，也未作为本轮缺陷。U06 叶 cell 缺外部 tapcell/全局电源上下文继续留给后续，当前 synthetic body_context 必填不变。有限穷举和 Python 对象反例不是全整数域或任意运行时篡改的形式证明。

本轮只新增本报告及 `independent-premerge-review/` 材料，并在 W009 reviewer 区追加结论；未修产品、正式测试、fixture/答案、历史证据、PM 段或 current-work。[提交前审计](independent-premerge-review/delivery-audit.json)核对授权路径、reviewer-only追加、240项源不变、链接与本次回执，并列出本次材料hash。**剩余必须修正项 1；交回 PM 修正和复核后再决定集成，不自行验收或合并。**
