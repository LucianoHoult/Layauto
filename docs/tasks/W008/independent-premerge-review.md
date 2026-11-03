# W008 独立合并前复核

2026-11-03（Asia/Shanghai）。主 reviewer：本轮独立会话 `/root`；输入、几何及证据专项分别由本轮 `/root/input_review`、`/root/geometry_review`、`/root/evidence_audit` 完成。上述 reviewer 均未参与 W008 实现、设计或原 review。本报告依据当前代码、真实捕获输入及新验证独立形成，旧 review/PM 结论只作为线索和待核验记录。

**结论：未发现阻止所审版本合并的问题；新增 finding 0，剩余必须修正项 0。建议 PM 按现有流程进入 main 集成和组合验证。** IR-01、CR-01 的关闭在本轮代码检查及反例中成立。没有需要交接的产品修复；本结论不代替 PM 最终验收，也不宣称完整 Stage 2、M1 或生产验证完成。

## 审阅身份与恢复

| 对象 | 实际核对 |
| --- | --- |
| 远端 | `https://github.com/LucianoHoult/Layauto.git`，fetch/push 均为 origin |
| 分支、审阅 HEAD | `codex/w008-geometry-base-occupancy`；`131f66dfadd77b5fb9073db999d6939051c3addf` |
| 审阅 tree | `f9452ae27842f82ee9ddd658477496ffced83c95` |
| 产品交付 | `aced62b0adda35fe7bcd8284a7354badc5b03649` |
| main 基线 | `765ff864f4341b91996f70f25723411eebc0d6c2`；远端 main 也为此 SHA |
| 工作区 | 初始 `/workspace/Layauto` 位于基线的 `work` 分支，staged/unstaged/untracked 均为空；保持原样，另在 `/workspace/work/w008-review` 恢复真实 Git checkout。该 checkout 开始审查及测试时干净 |
| 分支前进 | 首次及实跑前远端均为指定 `131f66df…`，无新增提交。交付到审阅 HEAD 之间的 `baad534…`、`131f66df…` 只涉及 U06/导航/任务和 PM 证据；runtime、tests、README、构建/typing 配置无变化 |

已检查 base→HEAD 的 121 文件 diff，其中产品模块 8 个；逐一审查这些模块及 W008 测试和 W007 guard 调整。Git 对象、历史、tree、空 diff 和 connectivity fsck 记录见 [恢复回执](independent-premerge-review/recovery/restore-receipt.json)，实跑环境及远端原始输出见 [validation](independent-premerge-review/validation/)。启动时默认 shell 网络权限未启用，显式使用工具支持的 network permission 后正常 fetch；未绕过代理或合成 Git 对象。

本轮提交范围仅为本报告、新附件及任务 reviewer 段追加记录。产品实现、fixture/答案、原报告/清单/日志和 PM 段均未修改。审阅完成后的报告提交 SHA 和最终远端完整 SHA 由提交后的 Git 核对及 PM 交接回复确定，不预写自身提交身份。

## 读取与判据

适用指令只有根 `AGENTS.md`，已查无局部 AGENTS。已读取 README、docs 导航、协作规则、local-setup 和 remote-development；读取 W008 全文的 A1–A8、后续范围、PM1，以及 plan、plan-review、code-review、execution、verification receipt/环境/清单/日志/包和 PM receipt/附件。

产品判据采用架构原文 §1.4、§2.2–2.3、§3.1/3.3–3.5、§4.1–4.4/4.8、§5.4–5.9、§11.2–11.3/11.10/11.14–11.15、§12.3/12.5；W003 contracts 和 MR-051/052/054/056；W005 输入及后续组合、W006 InputsReady/readback/interface-plan 和实际 DTO/repository 接口、W007 normalization/identity/seed/interface-plan 及实际验证/codec 合同。未用摘要替代这些原文，也未将 expected/spec/oracle 作为运行时输入。

## A1–A8 复核结果

| 要求 | 独立判断与可核验证据 |
| --- | --- |
| A1 真实组合、无 IO | 真实 W005 捕获和 W006 `prepare_inputs` 后的 repository readback 都进入相同纯构建链；构建/wire 期间禁用文件读取/resolve、subprocess 和 repository.read。多角色同时 alias 及 target 复用 source 的真实组合仍合法；attempt/terminal 不变。W007 source/target/差异/seeds 保持独立。见输入专项 24 项及完整回归 |
| A2 字段、bytes 和角色闭合 | `geometry_input.py:47` 固定 completed 来源角色；`:73` 区分首次获取与后续 alias；`:88` 起从同一 captures 重解所有消费的配置/owner/header/body/GDS 并 canonical 对比。成组篡改 value/completed、错 record 位置及同 hash 错角色不能借内容相同获准。IR-01 的 body 双来源和 header/body top/unit/profile/operator/scope 在 `:124`、`:159` 起落实；CR-01 的缺失首次 URI 被正确拒绝，定位 `site_config.yaml#/inputs/gds`，保留 9 项 completed |
| A3 精确几何、身份、单位 | 独立 `struct` 解包全部 40 条原 BOUNDARY，与每条产物的 XY/stream key/位置逐项比对；独立 rational REAL8 解码及 signed 32-bit 极值逆转换通过。`domain/geometry.py:198` 起无 float/截断/snap；provenance identity 绑定来源/top/位置，`layout_store.py:117` 的语义 comparator 使用排序 multiset。真实派生输入证明重排/反向或旋转起点保持语义 digest，删除一条重复 record 改变 digest。读取侧 unsupported stream/非矩形拒绝及已声明子集保持，未以 bbox 包络扩大支持 |
| A4 可重建分区 | `coordinate.py:74` 从各层 geometry 的唯一排序边界建立有限分区；`:96` 重新校验 algorithm/boundary/layout/axes。600 组独立分区、21,314 次精确点归属覆盖负数、边界、分数内点、空分区和大整数。固定 min included/max excluded，越界拒绝；physical/index 转换精确。此模型没有完整 coordinate_ref、合法 track 或制造网格承诺 |
| A5 逐 record 完整多占据 | 对每条投影 record 独立证明：fragment 位于原矩形及所属 cell 内、内部两两面积交叠为零、面积和等于原面积；因此并集覆盖原矩形。双向 refs 核对，无单值 occupant 覆盖。另构造手算面积 35/30/35 的负坐标、重复/重叠 LI 输入，同格保留 3 个 occupants。正常 38 条投影/41 fragments 仅作佐证。C1/C2 均保留而不进入主 occupancy；VIA/CONTACT/CUT 只投影自身层，6 个外部 body shapes 不进入本地 geometry |
| A6 constructor、codec、错误 | `LayoutDraft`、`BasePartition`、`BaseOccupancy` constructors 重建中立期望并拒绝漏项/重复/外来/错 cell/unit/geometry；`GeometryResult` 额外将 layout evidence 绑定到认证 input，不能用互相一致的伪草稿制造 success。完整回归覆盖递归不可变、alias、closed/versioned wire、canonical/hash-seed、非法结果及嵌套修改；新探针补四个 decoder 的 ValueError/KeyboardInterrupt/SystemExit 嵌套同对象传播。预期 InputError 保留定位和 completed |
| A7 依赖与范围 | 8 个产品模块的 AST/import 与 diff 独立检查通过。domain/state 无 parser/normalization/pipeline/repository/transactions 依赖；coordinate 不持有 occupancy。W007 guard 只按具名 W008 文件放行已捕获 bytes 的 decoder 及三个纯 state 模块，原限制保持。没有 physical edge、annotation/net stamp、CUT Boolean、terminal split、body/extraction、baseline/seal/no_change/terminal/Stage6 实现或成功声称 |
| A8 工程与身份 | 本轮新 Linux Python 3.12.14 环境完整 v2 **730 passed**，strict mypy **40 source files** 通过，pip check 通过。独立证据审计 29/29：235 项完整源码清单当前/交付均相符；84 附件按各自历史版本核对；13 命令/日志身份一致；实际 wheel/sdist 各 86 runtime 字节与源码一致。原 Mac 双解释器、build/两套干净安装按以下边界采信 |

## 新反例、原 finding 及信任边界

本轮未建立新增 finding，因而没有需分配严重度或修复范围的缺陷项；不将已正确拒绝的攻击或后续能力缺失列为 finding。所有反例和原始输出均保留，PM 可直接交给后续 reviewer 重放。

- [输入专项](independent-premerge-review/input/summary.md)：同 bytes 的 source/target 角色交换、外来同 hash 的 body 第二来源/header.layout/body.source_gds、中间 record 位置成组伪造、嵌套成功 wire 的认证、真正多 alias 组合及四 decoder 异常。原 CR-01 reproducer 保持不动，用捕获 `GeometryInputError` 的方式核对正确拒绝，未将其旧“成功”断言当作修后要求。IR-01 的跨文档绑定也对照实际代码和回归复核。
- [几何专项](independent-premerge-review/geometry/review-notes.md)：原始二进制、独立面积/交叠/点归属算术，以及 4 次真实派生 W005→W008 构建；没有调用实现生成期望或依赖正常数量自证。
- 中立草稿和最终认证职责保持分层。单独 `UnitBinding`/codec 不重新证明 REAL8 raw→parsed exact，单独 LayoutDraft 不重新解析完整 GDS；它们不是已认证 capture receipt。新 [中立边界探针](independent-premerge-review/geometry/unit_neutral_probe.py) 验证伪单位不能替换到现有 bound layout；最终 `GeometryInput` 重解 capture，`GeometryResult` 绑定输入与 layout。未找到绕过最终认证的 success 路径，不要求 domain/state 反向依赖 parser。

## 本次实跑与采信

本次 Python 为 **3.12.14**，独立 venv `/workspace/work/premerge-env/venv`，editable 安装本 checkout 的 `.[dev]`；pytest **9.2.0**、mypy **2.4.1**、PyYAML **6.0.3**。完整包版本、来源、平台和初始空工作区见 [environment.txt](independent-premerge-review/validation/environment.txt)。所有验证设置 `PYTHONDONTWRITEBYTECODE=1`，pytest 禁用 cacheprovider，mypy cache 位于仓库外。

| 实际命令/判据 | 本轮结果与原始材料 |
| --- | --- |
| `python -B -m pytest tests/unit tests/contracts -q -p no:cacheprovider` | **730 passed，550.32s**，exit 0；[输出](independent-premerge-review/validation/pytest.txt)、[完整 argv/时间/hash](independent-premerge-review/validation/pytest.json) |
| `python -B -m mypy --cache-dir /workspace/work/premerge-env/mypy-cache` | **40 source files，无问题**，exit 0；[输出](independent-premerge-review/validation/mypy.txt)、[回执](independent-premerge-review/validation/mypy.json) |
| `python -B -m pip check` | 无 broken requirements，exit 0；[原输出](independent-premerge-review/validation/pip-check.txt)保留 cache 不可写提示 |
| `PYTHONPATH=.:tests/contracts python -B …/input-independent/probe.py` | **24 项**，exit 0；[回执](independent-premerge-review/input/receipt.json)、[输出](independent-premerge-review/input/output.txt) |
| `python -B …/geometry_probe.py <checkout>` 和 `unit_neutral_probe.py <checkout>` | 600 分区/21,314 点/40 原记录/4 真实派生构建及信任边界检查通过；[回执](independent-premerge-review/geometry/receipt.json) |
| `python3 -B …/audit.py <checkout>` | **29/29**，exit 0；[回执](independent-premerge-review/evidence/audit-receipt.json)、[机器结果](independent-premerge-review/evidence/audit-result.json) |
| `python -B …/scope_probe.py`、Git 版本与范围核对 | exit 0；[scope 输出](independent-premerge-review/validation/scope.txt)、[实跑前远端](independent-premerge-review/validation/remote-before.txt) |

以上 `python` 指本轮独立 venv，唯纯标准库证据审计使用主机同版 Python；完整命令为各 JSON 回执中的真实绝对路径。绝对路径描述当次实跑，迁移后按[附件说明](independent-premerge-review/README.md)在临时目录重放，避免覆盖原输出。

[独立证据审计](independent-premerge-review/evidence/summary.md)已直接核验：

- 235 项 source manifest SHA-256 仍为 `30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881`，其完整路径集合、当前字节和 `aced62b` 字节均匹配；不是仅核对文件数量。
- 历史 84 附件清单中的任务文档只对 `aced62b` 验原 hash；其余 83 项对当前并对交付均匹配。保留原清单，未重写它来抹平 PM/reviewer 后续追加。
- 13 条最终命令回执与逐条 JSON、原始输出 hash、源身份均一致；修前 713 项材料仍单独保留，没有混作最终 730 项证据。
- 实物 wheel `64526a5b675048c55505fe4d81fa95408ca74c7c91176c1a4a098cafbca5740f`、sdist `e600e0735dadae75248675fcc4ec18355b48a29847e4af4424714bc5ec5345b4` 各 86 runtime 文件与受审源码相同；另独立检查 wheel RECORD 全成员 hash/size。
- 原 Mac Python3.10.22/3.11.5 各 730 项、各 40 模块 typing、构建、两套新安装及源码外 `-I -B` 组合 smoke：采信已核验日志、创建/安装命令、来源和全部 86 项已记录安装 hash；本轮未重跑这些历史命令，也未访问原 Mac 安装树。3.10 sdist 安装的 archive_info 缺 hash 如实保留，以实际附件、安装路径及文件 hash 相互佐证，未补写缺失元数据。

## 覆盖限制与 PM 交接

没有发现足以阻止 W008 合并的证据缺口。有限反例、算术验证及完整现有测试不构成所有输入上的形式化证明；未验证最大允许 record 数下所有极端重叠集的资源上界。本轮未在其他 OS/解释器重新实跑，未重新构建/安装历史包；上述采用证据与本轮实跑已明确分开。

内部 `drawn-layer-edges/1` 不证明完整工艺坐标、合法移动或物理连通。CUT/terminal split、spatial annotation/connectivity/body/extraction、lifecycle/baseline/seal、no_change/terminal、Stage6、真实 EDA/PDK/隔离生产准入继续属于后续。U06 的底层 cell 缺外部 tapcell/全局电源上下文需求继续有效；现有 synthetic body_context 必填不判为 W008 缺陷，本轮没有实现可选模式。

**PM 下一步：可对该审阅产品身份执行 main 集成及针对性组合验证，再作最终验收。本轮只提交 review，不合并 main、不删除分支、不启动下一任务。** 如果产品/测试/配置在本报告后发生变化，应按实际差异重新判断受影响结论；后续仅追加审阅/PM 文档不改变已核验的 235 项产品身份。
