# W012 A2 兼容方案独立 review

2026-11-11（Asia/Shanghai）。Reviewer：`/root/independent_review`。

## 结论

**方案 review 通过：有依据推荐所述两 owner 最小 owned typed pack，方案已足以直接派发有限实施；不是产品实施许可、性能验收或 PM 验收。** 新增必须项1（交付自检的生成输出链接依赖 A2-R01）已修正并独立局部复核，剩余必须项0；方案/参考 pack 本体未发现必须项。

推荐依据是实际 build/decode 确实反复进入这两个 encoder，原 pack 的父包装递归重冻子树机制可明确减少，有限小值证据显示完整字节相同且临时构造减少，实施边界只有两处私有 helper/调用点。未知的是完整路径中这部分的实际占比与维护收益，不能从全部 freeze exclusive、嵌套 cumulative 或小值计数推定生产改善。方案已把这一点列为未来完整三路同条件实测的停止/取舍条件，未承诺20%/50%或生产资源上界。

本轮交 PM 决定是否另派该最小实施或回 M1 网络标注。不能将本报告解释为允许新 writer/reader/memo、B、新公开 codec、删认证、合 main 或启动新子项。

## 独立性与受审身份

- Reviewer 未参与本方案、参考 pack、执行自检的设计或起草；只写本报告及 `review-*` 证据附件。只读子 reviewer `/root/independent_review/scope_identity` 独立核范围/身份/数值，未写文件、设计方案或运行产品路径。
- 隔离 worktree `/workspace/work/w012-a2-review`；detached HEAD `cbf20807a85d8350928fc6a604612384cb2727fd`，base 为 PM 准备 `842c5c1ea8f1d01bb3f04e4703f105e11f94158c`。开始时 staged/unstaged/untracked 为空；无 commit/push。
- 初审完整 diff 仅新增7个 A2 文件及 task 执行段8行。独立剔除唯一执行插入块后，task 全部原字节等于 base；AP1–AP5、PM要求/阶段、旧工具/证据、runtime、正式测试、fixture、current-work 未改。
- 后补交付材料以 root 工作区只读内容单独局部审查；不把其未提交状态冒作初审 commit。最终 Git commit 应绑定报告和实际生成输出，不要求交接文字自包含自身 hash。

| 受审材料 | SHA-256 |
| --- | --- |
| `plan.md` | `b5a30b7263140ce87320210694d48cefe76f1b66df81bfc28d133778136a7a7e` |
| `reference_pack.py` | `811b347559fd6c9faa1051e70227082c26f8f6da5467d4feca5badcf0f7b47ca` |
| `check.py` | `efb941f8a815dd644cbda9e33c1ac76a0de6eb3c26627cb072be43cd9bf9edb5` |
| `check-result.json` | `b3b179db6791c462e282bfe60b878d1413aeb46c6789b110d29f3421c15fb426` |
| `check.command.json` | `fbfd5bdadd1f2d1601ebb059281cab59cdb631a79d7751d24309b9038c0d53aa` |
| `check.stdout.txt` | `eb2ed9e6f15dae1baec29c08945181e9299ca674ec8d1ffee6efe3a5332cad42` |
| 初审 task | `91587f61b4462976e1a69a098d2e16a9ef1c2d2ba953c911323a091147bb64e7` |
| 后补 `delivery.md` | `ad3d5d1daff59b2721a6f10daf90a52a8457544d298b64d58c8ccd1d879f888b` |
| 修后 `delivery_check.py` | `28d770778766992326ae4f20757d03580cd9932cfa8de0a17767385b2bd630ae` |

后补 task 交接记录若只增加本 review 链接/结果，仍应由最终交付范围自检核原 AP/PM/task 字节未变；行为要求变化须复核受影响内容。

## 实际读取与核对

读根 AGENTS、README、协作规则、local-setup/remote-development、docs导航、W012 PM4/PM5/AP1–AP5、派发 review、原 P1 implementation-proposal；相关架构 §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15。目标仅有根 AGENTS，无局部规则。Cloud runtime 技能及环境状态已核：同一个环境 running、observations_current=true、网络 enforced；无安装依赖。

实读 domain.codec/FrozenMap/freeze/canonical/decode、regions.validate_closed_graph、publication及W007/W008/W009/W010/W011 codec 的字段分派/重建边界；W010/W011实际 builder/Result constructor，以及 W009 单次快照、W011别名/closed/exact字段和异常历史正式用例。没有把方案摘要代替源代码。

另读 A1 263项 source manifest、实际集成/工程回执、真实 after-profile、9份 after 性能样本和 performance-analysis/profile-summary。263文件（100runtime）对磁盘、A1冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`、实际merge `08dd232139918dc97b0a6d255aad237eb844686a`、PM准备提交逐项 hash 相同；9 after样本及after-profile source maps匹配。manifest历史git_head未被当作冻结证明。

## 核心判断

| 检查点 | 独立核对结果 |
| --- | --- |
| 真实收益归因 | 复算readback无插桩build/decode/最终encode中位为51.426606/66.114896/2.616473s；domain.codec插桩exclusive98.236572/124.771350/3.683182s，freeze/map家族89.925018/114.519416/3.362036s。方案明确后者含保留边界，不能当可省预算；嵌套cumulative不相加。direct/mismatch也独立保留数据，不把readback calls称为三路实测。 |
| 共同实际入口 | after-profile中local/channel encode次数：W011 build30/2，decode95/3，最终encode14/1；与真实代码链一致。优化两个encoder会作用于build/decode内的完整核源与尾部重编码，而不只是最后2.6s。方案未承诺降低所有lower codec或重建成本。 |
| 可实施性 | 两个现有 closed encoder 保留根exact type与原图validate_closed_graph，采用各自原_SPEC和分派顺序，唯一切换是envelope内pack表达式。每个字段、tuple、delegate、map/scalar分支算法明确；旧_pack完整留给_unpack的重建值比对。无需执行者再决定格式、owner或认证边界。 |
| 纯临时构造 | 拟减少的是encode包装FrozenMap及父包装对子树的重复freeze。canonical入口完整freeze、普通输入快照、public FrozenMap实现、DTO constructor、domain.decode构造、所有旧_pack重建仍保留。私有allocation第N次故障次数可变与公开故障合同区别有明示，不借此豁免正式测试。 |
| 别名/exact/来源 | map叶在原处理位置freeze，tuple立即物化，scalar原freeze；owned dict仅存本操作产生的值。原图closed检查先于copy，仍拒绝MutableText、DTO/Fraction子类、equal-object和可变集合。完整来源/run/owner/原bytes没有摘要替代或按相同hash合并。单次集合快照没有被改为两次遍历。 |
| 字节等价 | 对照原字段/标签/次序与完整delegate bytes，归纳到同类型完整冻结树；不只靠Python数值相等。原_wire/json.dumps/UTF-8不动，排序/escape/rational/hex/大整数及Unicode错误处理仍由旧算法。独立小值核bool/int/Fraction等值但字节不同，未发生折叠。 |
| 公开重建/第二次认证 | 实际W011 builder先_require_input，Result constructor再_require_input、replace(value)、_evaluate及全字段字节比较；各decode先domain canonical检查、_unpack公开constructor、旧_pack全值检查、最终encode原bytes比较。全部保留。test_w011_exceptions第二次故障的object/cause/context/suppress不能移除；已有handler位置不变。 |
| 验证与范围 | 方案固定未来URI/RunRequest/cache/roots/GC、完整三路逐字节和无插桩前后，开发先新增/受影响、最终新冻结双全量/typing/构建/双干净安装。当前runtime不变，采信同源A1工程证据成立。wire降幅0；未来收益不足交PM回M1，未扩B或删认证。 |

收益仍有局限：原profile无caller边，不能准确分割两个owner包装占总freeze的份额；新dict树也可能增加峰值保留，lower重建/旧_pack/巨大完整wire仍保留。720336KiB残余峰值未逐allocator归因。这些是已经披露的实测前风险，不是本次方案承诺的成果；小值构造减少足以支持两处有限实现的候选选择，不能替代未来完整收益判断。

## 有限独立见证

没有直接重跑会覆盖原check-result的check.py。新增 [review-probe.py](review-probe.py) 在隔离worktree运行，命令/原输出/结果见 [command](review-probe.command.json)、[stdout](review-probe.stdout.txt)、[stderr](review-probe.stderr.txt)、[result](review-probe-result.json)：

- 263项磁盘身份及脚本hash、task原区字节与base相同。
- 34个有界私有subvalue结果，对照实际旧_pack与参考pack，包括local/geometry/effective/semantic/captured分派或原来即拒绝的分支。
- bool/int/Fraction字节保持不同；替换原exact FrozenMap存储后，已pack叶的独立快照不受影响。
- 一个真实neutral ChannelRef完整小wire和原公开decode重建；foreign scalar root原图拒绝一致。

exit0、stderr空。只测试小值/中立叶，未调用完整Result/build/readback、未替换或monkeypatch完整runtime，也不计产品耗时。

执行者原6个真实小root计数、逐字节、原decoder对照与22个private subvalue证据结构可信；其中BrokenMap异常见证是私有helper输入，不被当作公共Result异常链已运行。真实公开第二次认证/嵌套故障的保持依据为本方案不变的调用边界与未来必须保留的正式回归，不称本次重新执行了那些重型用例。

## Finding 与修正复核

| ID | 原 finding、反例与影响 | 执行处置及独立复核 |
| --- | --- | --- |
| A2-R01（必须） | 新增交付自检先遍历delivery.md的所有链接并要求exists，随后才写自身delivery-check-result；外层command也在结束后才生成。首次干净执行时，即使其他输入/review链接存在，仍因未来输出delivery-check.command.json缺失而失败。不能靠预造passed结果解决。初审checker SHA=`596b202e94ed7585fa10d4451d5be5b9965f2275bf9478cc53dd407d44d2c29b`。 | 执行者接受，保存原源为delivery_check-before-R01.py.txt；仅豁免本次明确将生成的command/result/stdout/stderr四链接，其他链接仍检查，完成后由外层及最终Git绑定真实输出。Reviewer隔离复现原存在性循环exit1，再执行修后实际AST赋值/循环：四输出均不存在且未预造时通过，另加普通缺失链接仍拒绝。修后checker SHA=`28d770778766992326ae4f20757d03580cd9932cfa8de0a17767385b2bd630ae`。**已关闭。** |

原始存在性读数见 [review-delivery-initial.json](review-delivery-initial.json)。[原问题复现](review-r01-reproduce.py)及其 [command](review-r01.command.json)/[stdout](review-r01.stdout.txt)/[stderr](review-r01.stderr.txt)保留预期exit1和真实AssertionError；[修正复核](review-r01-verify.py)及 [command](review-r01-verify.command.json)/[stdout](review-r01-verify.stdout.txt)/[result](review-r01-verify-result.json)为exit0。没有覆写/删除执行者原证据，也没有修改其工具或方案。修后完整交付checker由root在收到本报告后实际运行，当前不把尚未运行的命令写成通过。

## 限制与停止点

本报告验证方案可派发性、静态完整合同与必要有限附件，不验收尚不存在的产品diff或完整收益；未跑小时矩阵、18条benchmark、完整Result或重比原大wire，未重读旧安装树。A1双1656/typing54/构建/安装按相同源码及已验收回执采信。

原finding及修正关闭保留。执行者补齐真实最终范围自检/提交/远端SHA后交PM，本报告不代写PM阶段、不合main、不自动实施或推进下一子项。

## 最终交付局部复核

Root收到本报告后首次运行修后完整delivery checker：命令开始 `2026-11-11T06:52:42.709366+00:00`、结束 `06:52:42.803270+00:00`，Python3.12.14，HEAD仍为受审cbf提交，**exit0 / stderr空**。Reviewer随后只读实际command/stdout/stderr/result，确认command/result/stdout/stderr四个真实产物存在、result.status=passed，全部material_sha256与当前文件一致；并非预造结果满足链接检查。首次产物另行原样保留为 [command](delivery-check-initial.command.json)、[stdout](delivery-check-initial.stdout.txt)、[stderr](delivery-check-initial.stderr.txt)、[result](delivery-check-initial-result.json)，不以最终刷新覆盖它们。实际stdout为：

```text
PASS: only A2 attachments + inserted task execution section differ from PM preparation
PASS: original task requirements/AP/PM bytes and all other protected paths unchanged
PASS: plan/delivery links, finite tool identities and original exit/output evidence
```

最终task执行段仅增加本review链接、A2-R01关闭/有限派发及交PM说明链接，SHA-256为 `cb35c8384758e290e4ce5874c18738d380b60076f7ad7afd06640d008367819f`。Reviewer再次剔除执行插入块后比对base完整原字节相同，PM/AP/阶段未改；plan/check/reference三文件也逐字节等于受审 `cbf20807a85d8350928fc6a604612384cb2727fd`。后补交接材料没有扩大候选、验收或产品授权，**局部复核通过，新增/剩余必须项0，A2-R01关闭保持。**

本段不绑定会因报告hash刷新而变化的seal result自hash。Root在复制本段后如需刷新同一范围封存，应保留首次四原产物，再由最终Git绑定新封存；这只是文档/证据身份刷新，不是新受测产品或新性能实验。本报告的推荐、限制与PM停止点不变。
