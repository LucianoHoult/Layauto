# W014 独立最终工程专项（准备中）

Reviewer `/root/plan_review/final_evidence_review` 未参与runtime、正式tests、工程
工具或smoke实现。此专项只写review材料与独立只读审计脚本，不运行新捕获链、
codec重链、全量、build、安装或烟测，不代PM验收。

开始时HEAD为`40559e0186f7d80bb8a7f3256c900e0fadd66191`；工作区有本轮W014
产品及执行/证据材料。最终候选source_id为
`8ef803c96ed693a1f97843fa5dede942151e76c326a9b5cd29f7b92a3377048d`。
contracts-r4定向正在运行，最终工程矩阵尚未开始，本记录不宣称通过。

## 已读与静审范围

根AGENTS、README、协作规则（含verification-reuse）、环境说明、W014任务、
方案及主code-review；完整读取prepare_final/run_check/source_identity/installed_smoke。
未以先前会话摘要代替这次实际工具检查。

最终runner实质核：精确source/资源clearance、单一选定源码快照、双解释器来源
身份、双完整collection保留1731 baseline IDs、实际pytest通过数量、strict mypy/
pip check、wheel/sdist完整runtime字节、全新3.10 sdist/3.12 wheel安装、源码目录
外`-I -B`三路实际smoke、安装包路径和全部runtime字节、最后再次核源/工具身份。
21条命令有exit code、原stdout/stderr、时间和hash；失败不会写passed receipt。
两个matrix每个内部串行，build及两个安装smoke在matrix后，符合调度边界。

smoke的三路断言涵盖八端/shared gate、独立body链/精确边长/包围、BN/BP本地
unknown、原W013覆盖缺口、W011 4对5、readback unsealed/checkpoint/无terminal、
公开完整roundtrip/digest与伪造拒绝，且不从oracle/spec/expected解析答案。

## EG-01：mismatch active四边margin被错误套用normal常量（已关闭工具缺口）

原installed_smoke.check_body无条件断言MN0 active margins为`(20,20,20,20)`；
terminal_checks在extraction-mismatch也调用它。实际失败样本ON上边是64nm，
BODY_N上边90nm，故四边应为`(20,20,20,26)`，最小margin仍为20。否则长矩阵
结束后安装smoke会因错误测试常量失败。

独立标准库直接读取两份raw GDS的LAYER/XY并计算四边：
[原几何证据](installed_smoke_mismatch_geometry.before.json)。保存的
[原工具](installed_smoke_before_mismatch_fix.py) SHA-256为
`6bb0f70335fc6b0bbeb1090fec80521cc460f533dcb2fe25ca102657c34d3822`，
见[身份记录](installed_smoke_mismatch_tool.before.json)。本专项没有执行完整安装
smoke来制造该失败；以上结论来自确切的源码断言与实际GDS数值。

执行者已使check_body显式接收case，normal/readback仍核20四边，mismatch精确
核20/20/20/26，没有弱化为仅看最小值。修后工具SHA-256为
`25eea1ea828d1451c8ffcb5a9fd8d56a8131cb3048169e4a6713d5a72947257e`。
本reviewer用[轻量helper probe](installed_smoke_mismatch_probe.py)，只从独立raw
GDS数值构造tool-check stand-in，调用保存的原helper和修后helper：
[before](installed_smoke_mismatch_probe.before.stdout.json)为normal接受/mismatch
AssertionError，[after](installed_smoke_mismatch_probe.after.stdout.json)为两者接受。
没有构建或伪称该stand-in为captured product result；据此关闭工具缺口，实际双
clean安装烟测仍必须最终运行。

## 最终独立审计准备

[final_engineering_audit.py](final_engineering_audit.py)为本专项独立编写，只读未来
工程原产物。已做语法/CLI检查，**尚未对不存在的最终证据运行通过审计**。
后续命令形状：

```sh
python -B docs/tasks/W014/review-evidence/final_engineering_audit.py \
  --root /workspace/Layauto --evidence docs/tasks/W014/verification \
  --source-id <实际最终source_id> --freeze-commit <实际冻结commit> \
  --out docs/tasks/W014/review-evidence/final_engineering_audit.stdout.json
```

审计将独立核源/完整tar/Git/live身份、evidence manifest全成员和hash、原21命令
与原输出、双collection/pytest/typing、包与安装111 runtime、pip原安装artifact hash、
源码外三路smoke实际JSON、readback状态、真实时间排序。缺receipt、failed receipt、
任一hash/成员/命令/数量/版本不闭合均不能产生passed审计。它不会重新执行产品
测试、构建、安装、捕获或codec，也不复制整份大wire或安装树。

当前剩余工作是等待指定最终工程产物和冻结版本，再运行只读审计并补结论。
源/test/config/依赖改变、原证据缺失/失败或发现新风险时按实际影响复核；仅换
reviewer及文档补记不触发重复双全量。完整M1、真实EDA/PDK、生产准入和PM验收
继续在本专项范围外。

## 恢复点更新：R5候选，最终矩阵尚未开始

主reviewer交接的新候选source_id为
`2d46bbdaccd858af936d37427ec8bad11d0bb11074d92cddb901da6197ecf639`
（285个selected文件、111个runtime）。原contracts-r4定向真实16 passed/1 failed
暴露malformed codec outputs的KeyError；另Result.value保留inputs被compact编码
丢弃的问题归主报告CR10/CR11。原失败和source身份保留，不能把旧R4候选当成已
跑过最终矩阵。

主reviewer说明codec已作完整raw typed存储字段比较，原input继续完整公开认证，
不调用原不可信property；collection-r5为1873项、typing-r5为65源成功，修正定向
及独立after probes已通过。以上是交接的恢复事实，本专项尚未自行审这些runtime
修正或重跑产品；由主code-review负责其finding关闭。

资源R3的W014三路仍执行中，旧W013 reference按原身份采信。最终工程矩阵仍未
开始，最终通过审计尚不存在。本专项工具/EG-01不需要因此改动。
final_engineering_audit.py的source_id和预期测试总数分别取命令参数与实际最终
receipt，未硬编码旧8ef候选或旧测试总数；1731仅是已验收W013 baseline的固定
身份要求。收到实际冻结commit/source_id与完整工程产物后，再按其真实身份核验。

## 恢复点更新：metadata R6候选，资源R4窗口

当前候选为
`998aa8052b3a6c89e3f87e029134ef8f6601535616c8b327d5ada44a29351a84`。
本专项只读核`development/metadata-r6-source.json`实际记录为286个selected文件、
111个runtime文件。主reviewer交接说明collection为1889项、typing为65源，
CR12 graph证据metadata修正的六种独立after均已通过；runtime候选仍未最终freeze，
工程矩阵尚未启动。本专项不把这些交接事实写成自己新跑过的产品结果。

root当前独占资源R4窗口，本专项只做docs/scripts只读复核，不运行产品链、pytest
或codec。final_engineering_audit.py无需为1889或新source改代码：总测试数取最终
receipt并逐解释器对collection/full原日志核验，source_id取实际命令参数；selected/
runtime数量也从完整manifest和实际包成员核对，没有硬编码旧285/111。1731仍仅
用于已验收W013 baseline完整性。

已重新对照prepare_final.py资源门：实际R4 clearance在runner执行时必须绑定同一
最终source_id及direct/readback/mismatch三路；若workers=2还须明确
parallel_matrices_safe=true。runner将该原clearance复制到最终证据owner，本审计
再核其decision/source/cases及hash，因此不依赖旧R2/R3的文件名或source。
当前尚无R4最终clearance或最终verification receipt可供本专项通过审计，仍须待
实际冻结/工程完成后再执行。

本次只做脚本静态/语法检查及manifest读取；EG-01修后smoke工具SHA仍为
`25eea1ea828d1451c8ffcb5a9fd8d56a8131cb3048169e4a6713d5a72947257e`，
没有新的工具修改或确认阻塞项。其余源码/测试/metadata findings及最终总review
结论由主reviewer维护，PM验收仍在本专项范围外。

## 恢复点更新：实际冻结版本，等待最终verification

主reviewer确认最终冻结commit为
`66f5b1e5369549ed8df361f89f099acfd2f39e17`，source_id为
`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`，
286个selected文件、111个runtime、1889项测试，strict typing范围65源。
相对资源R4受测`998aa805…`仅有test_contracts一处else修正；主reviewer已完成
301项delta及300项freeze身份核验。这些结论归该主review证据，本专项没有重复
资源测量或产品执行。

实际`resource-clearance.json`已给出status=passed及parallel_matrices_safe=true，
原字节SHA-256为
`b9c699e9d2284fbc40a32641c98a89f4293e9c244ee50f203f5298f0153a2222`。
root即将按此冻结版本启动最终verification；两个解释器矩阵独占产品资源窗口，
本专项仍只更新docs、等待实际receipt，不运行pytest、codec或其它产品链。
smoke工具保持`25eea1ea…`，审计脚本继续使用参数化source/receipt数量。

当前不能把资源clearance、冻结或即将启动写成双全量/构建/安装已经通过。
实际最终receipt、原输出和包/安装身份全部完成后，主reviewer会触发本专项只读
final_engineering_audit，再绑定上述commit及实际source_id记录核验结果。

## 最终工程部分产物只读检查（receipt尚未生成）

收到主reviewer“3.12安装烟测仍在运行”的通知后，本专项只读已完成产物，未调用
尚缺receipt的final_engineering_audit，也未运行产品链。冻结source仍为
`c7769fcb…`，没有提前给整体passed结论。

实际原输出核到：3.10全量1889 passed（pytest报告10784.59秒），3.12全量1889
passed（7731.42秒）；双strict mypy各65源成功，双开发pip check exit0。两个
collection各1889个唯一ID，完整保留1731个原baseline ID。已完成命令各自原
stdout/stderr hash与命令回执相同。build命令exit0；本专项重新读取wheel与sdist
全部runtime成员，两包各111个文件逐hash等于冻结runtime manifest。

3.10 clean sdist安装三路smoke的实际JSON包含direct/readback/mismatch，公开
roundtrip均true，MN0的normal/readback为5、mismatch为4，而source声明仍为5；
attempt/checkpoint未变且terminal不存在。原smoke命令exit0（461.918秒）。
结果记录于[部分只读核对](final-engineering-partial-check.json)；该记录明确最终
receipt不存在，3.12安装smoke完成回执仍pending，不构成最终工程审计通过。

截至此只读检查，已完成产物未发现新的静态疑点或身份缺项；剩余项是3.12实际
烟测完成、installation identity/最终receipt/evidence manifest形成及统一末尾
身份核对。等待主reviewer明确receipt-ready后，才运行最终独立只读审计。

审计准备时另发现本专项脚本最初假定pip报告总有`archive_info.hashes.sha256`。
实际3.10 clean环境的旧pip报告只有`archive_info.hash="sha256=…"`，3.12报告
两种字段都有。已修正**本专项审计脚本**兼容两种明确SHA-256格式，若两者并存
则必须一致，仍拒绝缺失/格式错/冲突；没有改产品或工程runner，也未降低artifact
hash要求。原审计脚本快照及修正身份见
[兼容记录](final_engineering_audit.pip-report-compatibility.json)。只读提取两份实际
pip报告的hash均成功，构造的矛盾hash控制被拒绝；没有因此执行最终审计或产品。

## 最终独立工程证据审计结论

收到主reviewer明确receipt-ready后，本专项实际执行独立只读审计，**840项检查
通过，工程证据身份与实际命令闭合；未发现剩余工程证据阻塞项。**
这不是重新运行产品、总体代码review或PM验收，前文“等待/准备中”记录保留其
当时范围，最新工程结论以本段为准。

受核冻结commit为`66f5b1e5369549ed8df361f89f099acfd2f39e17`，完整source_id为
`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`。
实际命令、完整检查列表和结果见
[独立audit输出](final_engineering_audit.stdout.json)、
[命令stdout](final_engineering_audit.command.stdout.txt)及
[命令stderr](final_engineering_audit.command.stderr.txt)（为空，exit0）。

独立读取并重算286项源码/测试/config/input的live、完整source tar和冻结Git
archive逐字节身份；核完整evidence manifest成员与hash、21条实际命令exit0及其
原stdout/stderr/hash/时间、三个工程工具与clearance、真实阶段排序；两包和双
clean安装的全部111 runtime字节均等于受测冻结源，没有以文件数或HEAD相同
代替内容核验。

| 已核实际工程事实 | 原结果 |
| --- | --- |
| Python3.10全量 | 1889 passed；pytest原文10784.59秒，命令回执10787.714秒 |
| Python3.12全量 | 1889 passed；pytest原文7731.42秒，命令回执7733.730秒 |
| 双collection | 各1889唯一ID，保留全部1731 accepted baseline IDs，新增158 |
| 双strict mypy/开发pip check | 各65源成功；两份pip check exit0 |
| wheel/sdist | 各111 runtime成员逐hash匹配冻结源 |
| 3.10全新sdist安装 | 源码外`-I -B`三路真实smoke exit0，461.918秒 |
| 3.12全新wheel安装 | 源码外`-I -B`三路真实smoke exit0，328.685秒 |

两份实际安装smoke的direct/readback/mismatch JSON均包含八端关系（六个本地+
两个独立body）、14/8/6本地图及两个unknown本地body component、完整公开
roundtrip、原MN0 4对source5差异；readback的attempt/checkpoint未变且terminal
不存在。实际安装使用记录中的原artifact SHA，两个pip报告的显式SHA格式均
严格核对。3.10/3.12导入路径均来自各自clean site-packages；source外cwd与
`-I -B`命令也按原记录核验，未把本checkout当作已安装包。

最终receipt SHA-256为
`fbfd34d4c63e00c6e1cdd5a340487be6306a10bb0707605a229b4eaa527fe938`，
evidence manifest为
`0a507f3c1d8d667d84a3d5fc59210c79b2d9845bab6d4f3def75331a3c66baa6`，
独立审计脚本为
`3988fc522ea402db9e972a762f35dc7a19b68fd5d72eabe2a99b1a491600a184`，
审计输出为
`1c85a2554373971a52cf0f435fbf8556f7a53dd307adbedc12a14fbb5b2fafc7`。

本次实跑仅为上述标准库只读原产物审计；双全量/typing/build/安装smoke按精确
原身份采信，不重复产品链或复制大wire/安装树。未覆盖主产品算法重新review、
实际main集成、完整M1、真实EDA/PDK或生产准入；这些不因工程证据闭合而通过。
源码/test/config/输入/依赖变化、证据缺失/失败或新风险触发受影响重核；仅文档
补记或换PM/reviewer不触发重复双矩阵。总review及PM最终接收仍由各自owner完成。
