# W014 独立合并前复核

2026-11-16，独立 session reviewer；未参与 W014 方案、实现或正式测试编写。
**结论：未发现新的必须修正项，可交 PM 进行 main 集成及必要组合验证。**
这不是 PM 最终验收、实际合并或生产准入。

## 被审身份与恢复

- base/main：`8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4`。
- 实际远端接收 head：`716e7be1aa0e1042958f4e82eb081ae7a4f6e141`；执行交付：
  `6033537add14beadbbc441fdcfe5f6ef905ea948`。
- 产品/测试/config 冻结：`66f5b1e5369549ed8df361f89f099acfd2f39e17`；
  source_id：`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`。
- `git diff 66f5b1e… HEAD -- layauto_v2 tests pyproject.toml` 为空。
  当前与 base 的产品相关差异为15路径：5新 runtime、导出/typing两路径、8新测试/helper。
  未改旧 codec、正式 fixture、答案或 A2 产品。仅根 AGENTS 适用。

最初 checkout 为干净的 `work@8f3f395…`，无目标引用及独立 prompt。默认沙箱的
代理连接失败；禁代理直连又因 DNS 失败。保留环境原代理并使用获准联网的命令后，
`git ls-remote` / `git fetch origin codex/w014-terminal-body-relations` 成功，随后切到
目标分支，按实际 prompt 恢复。本 session 自写的未提交阻塞记录已移除，其历史在此
保留；没有覆盖用户已有修改。没有改持久代理/DNS/TLS 设置，无需用户另行配置。

## 独立核查及 A1–A9

已读取任务 A1–A9/PM1、独立 prompt、方案及方案 review、执行、代码 review 原
CR01–12/最终复核、body 调查、U06提案、资源最终选择和 verification/receipt。
回查架构 §2.3/3.3/3.6/4.5–4.7/5.6–5.9/11.2/11.5/11.9/11.15、roadmap U06、
W003/W004现行 body 合同、REQ-01及实际 context/tech/raw。审读5新模块、导出及
typing差异和新增测试；两侧核 W007 normalize、W009 operator、W010完整认证/
local graph、W011 association/topology/comparisons、W013 targets/components/
coverage及 reader body有序两来源调用。没有仅据执行摘要作结论。

| 项 | 独立判断与依据 |
| --- | --- |
| A1 | 单个成功 W010 Result 经原完整 encode/decode 重认证，统一 normalize产生channel/net seeds；neutral校验 source/seed/owner/capture集合与query run/database，body两来源按context/GDS有序绑定。captured入口和neutral自洽的证明边界明确；后者不能单独证明捕获真实性 |
| A2 | 逐device×D/G/S/B，D/S消费现行ordered topology，不做swap；G允许两个target共用gate node。expected来自source、observed来自W013，target intent另存。实跑正常八端、共享gate双target及body本地observed为空；无同名建边或pin access承诺 |
| A3 | 实核 actual GDS/top/FRAME/单位、exact本地对象匹配、external独立scope、typed tap唯一正面积接触和FRAME左边正长度续接。观测只能在精确rail锚后产生，并继续合入真实component冲突。独立错误claim仍observed VSS，45.05反例不能借component已知而通过 |
| A4 | 全active、local/external域全部异型body pair及全部external taps审计，含orphan；原local T05保留。独立手算并实核active四边20/20/20/20与20/10/20/20、tap最小body8/rail2；tap零包围时仍保留contact与八端事实，另报rule violation；不升级成全部mandatory通过 |
| A5 | 七body见证及缺context/operator按实际reader/W014边界对应，提供但错误不降级普通缺项。REQ-01独立真实raw改为901/20，MN0.B变indeterminate且无observed；保留精确Fraction。边/点/面积及异常边界另静审与原独立证据核对，未伪造sealed或terminal |
| A6 | 每个准入source device均保留四端；缺channel亦保留诊断targets。原FIN4对source5、完整target differences、W013 issues/coverage仍可达；有限端比较、channel比较和source汇总分开。汇总equal不表示完整model/VT/extraction/LVS |
| A7 | 原native/storage校验先于复制；所有dataclass/FrozenMap字段及EvidenceRecord/SourceRef外壳重构；合法init=False class default兼容。codec对Result所有保留value/input/facts作typed canonical核对，不只验证compact投影；decode先限制foreign root，未用任意异常catch伪装输入错误。实跑公开完整roundtrip和原SourceRef额外可写存储拒绝。只有一份完整W010捕获，W011/W013为neutral共享，资源另见下 |
| A8 | 四类生产单cell样张保留本地已知，区分父级/global未知、body物理未证、错误已提供证据和人工意图；可信替代需scope及baseline LVS＋body/boundary invariant。允许分析不等于允许提交；仅设计，现reader仍必填body_context，未新增生产格式或重问D1=A |
| A9 | 方案独立门在实施前，原代码review/修正链可追；本次重新核最终工程身份与原输出，按身份采信双1889、双typing65、build/双clean安装三路；未重跑完整矩阵。PM尚需实际集成身份和相称组合验证 |

## 本次实跑与原证据采信

实跑环境为当前主机 Python3.12.14，未安装依赖。重型公开路径串行；不保存新的
完整wire或安装树。以下脚本及stdout/stderr均为本次新增，不覆盖历史证据。

1. `python -B docs/tasks/W014/pm-receipt-check.py`：exit0，286 live/frozen/
   delivery/tar源、81证据hash、21命令及两包各111 runtime一致。
2. `python -B docs/tasks/W014/independent-premerge-probe.py`：exit0，78.289秒。
   一次实际reader→W008→W009→W010→W014 build/encode/decode完整往返；随后
   共用未改local几何，以重新读取的实际临时body/query捕获构造neutral变体，
   不把这些变体说成完整captured Result认证。正常、false claim、零tap包围、
   orphan tap、仅MN选错body、901/20及原SourceRef alias均按独立断言通过。
   [脚本](independent-premerge-probe.py)、[原输出](independent-premerge-probe.stdout.txt)、
   [stderr](independent-premerge-probe.stderr.txt)。脚本中常量只作review断言，不进入runtime。
3. 重新执行原 `review-evidence/final_engineering_audit.py`，参数为本仓库root、
   `verification/`、上述source_id及freeze commit，`--out` 指向
   [本次审计](independent-premerge-engineering.json)：exit0，**838项**通过；
   [stdout](independent-premerge-engineering.stdout.txt) / [stderr](independent-premerge-engineering.stderr.txt)。
   历史840还包含原主机两处仍在的安装树即时复查；当前那些临时树不存在，所以本次
   不声称再次核到它们，已有安装原输出、runtime清单、包字节与收据仍闭合。
4. `python -B docs/tasks/W014/independent-premerge-resource.py`：exit0。
   [脚本](independent-premerge-resource.py)、[最终输出](independent-premerge-resource-final.stdout.txt)、
   [stderr](independent-premerge-resource-final.stderr.txt)。25个引用文件hash/大小、
   三路R4原身份及原cost重新核对；将已记录的测试小补丁精确反向重建并核hash，
   证明测量源到冻结源仅该测试分支变化，106个旧runtime完整字节相同。

按完整身份采信的矩阵仍属于原 `verification/`：Python3.10.22/3.12.14各1889，
typing各65、build、双clean安装源码外direct/readback/mismatch，21原命令exit0。
本次审计重新读取原pytest/typing输出、安装来源/包及环境/日志收据，不冒称这些
是本次重新实跑，也不把空CI当通过。

CR01–07/09–12原finding及关闭证据与当前修后分支一致：存储全集、class default、
status/来源/错误隔离/FRAME/冲突传播、foreign root、所有保留input、投影次序、
Evidence外壳问题均有对应防护。CR08原公开漏洞归因撤回正确，真实改变gate
operator在W009即拒绝；未重新列为W014阻塞。EG01是smoke期望错误，其修后实际
双安装证据已闭合。原失败与修复历史不改写。

## 资源与本次审计工具失败

采用原R4 clean direct、原R4 readback/mismatch三条各自路径/hash；不称为全套新
独占suite。测量源`998aa805…`、旧W013 reference `803b4c4f…`保持原身份；
原direct与6.30秒probe的交叠披露仍有效。公开阶段总耗时比约1.133/1.031/1.093，
新增wire345944/345944/344703字节，峰值196.40/491.91/204.29MiB。
W010公开decode为1/1/2，不表示其内部每个对象只重建一次。本次没有性能重测；
单样本和有限fixture不是生产/最大输入或稳定性能保证。

保留两次本次工具失败，均不作为产品finding：

- 直接调用历史R4审计的main、将OUT改到临时目录时，原脚本要求live全部等于
  R4测量源，在已知测试delta处断言失败。[stderr](independent-premerge-resource.stderr.txt)
  及[stdout](independent-premerge-resource.stdout.txt)保留；不是该历史审计原时点失效。
- 新资源脚本初次把reference快照中的5个W014模块也计入“旧runtime”，106计数断言
  失败。[初次stderr](independent-premerge-resource-after.stderr.txt)和
  [stdout](independent-premerge-resource-after.stdout.txt)保留。修正为明确排除那5个新增
  模块后才得到最终通过；其它完整文件集合/精确补丁/hash断言保持。

## PM 接手与限制

本轮只写本报告、有界脚本/原输出和任务reviewer追加段；没有修改产品、正式测试、
fixture、历史报告、PM要求/阶段/验收或current-work。没有合main或启动后续任务。
原分支按prompt以项目noreply提交推送，交接回复给实际远端完整SHA。

未覆盖：完整M1、其它mandatory、通用PDK/S-D策略、真实EDA/LVS/生产、baseline/
no_change/publication/Stage6。本次没有重跑readback和mismatch全捕获，它们的工程/
资源证据按上述身份采信。PM实际合并前再次核main/head；如源/测试/config/依赖/
输入变化、冲突或组合行为变化、证据不闭合或出现新风险，按受影响范围补跑。
产品源改变后重新冻结并履行最终矩阵要求；仅本轮review文档变化不触发双全量。
