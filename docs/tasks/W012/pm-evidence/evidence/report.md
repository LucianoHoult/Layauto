# W012 PM 只读证据专项

结论：交付 `5085f994f0bd4b0c39f7ac1ccdbcacc43d281720` 的调查测量与工程证据可支持 PM 接收 P1/P2；本专项新增必须问题 **0**。这不是产品优化验收，也不批准 A/B 的目标或实现。独立脚本 [check.py](check.py) 实际通过 **1048 项轻量检查**，完整值见 [result.json](result.json)，实际命令与原输出见 [command.json](command.json)、[stdout.txt](stdout.txt)、[stderr.txt](stderr.txt)。检查前后仓库均干净，本专项只写本目录。

本次实读根 AGENTS、README、协作/本地与远端环境规则、W012 派发/计划/成本分析/独立 review；直接审读 `probe.py`、`run.py`、`memory_probe.py`、`summarize.py`、`validate_evidence.py`，并回查 `domain/codec.py`、W011 builder/constructor/codec 及第二次认证故障合同原文。没有执行重型 baseline/profile/内存补测、正式产品测试、typing、构建或安装。

| 判据 | 本次实际核对与结论 |
| --- | --- |
| PP1 | 当前 HEAD、PM 准备 `f3698b7…`、main 起点 `0a3326a…`、W011 冻结 `e89bdaa…` 的262源 SHA256 全等；100 runtime 的相对路径 manifest 与源 manifest 一一匹配，原 snapshot262项匹配。工具 `probe.py`/`run.py` 与冻结 `cfaf85e…` 一致，原轻量自检绑定相同 hash。preflight 先于首条重型命令。固定输入/cache/RunRequest/一次 GC/保留顺序可在代码及计划定位，六路解释器/平台等于 preflight。当前主机35个 mismatch target均未存在，但35项 origin 的 bytes/hash均实核，六路 mismatch捕获逐项匹配该可重建清单；没有把本机目录缺失写成测量失败，也没有虚称本机重跑。 |
| PP2 | 六条命令实际 argv、per-path命令、receipt、原 stdout/stderr hash及各阶段原计时互相一致；时间戳无重叠。launcher 每次 `Popen` 新解释器并等待退出再启动下一条，baseline分支不启用hook/cProfile。代码和结果保留完整公开Result及roundtrip、36项evaluation和全部crossing、正常5/7、mismatch4对source5/一项差异/touch、原局部图/T05/body及readback attempt/checkpoint unsealed不变/无terminal。三路径每条31捕获/280706B。 |
| PP3 | 原始 profile 的完整wire长度/hash、capture清单、输入URI及语义结果各与本路径baseline一致。独立复算outer hex、调用数、全阶段domain.codec disjoint exclusive占比、W011/W010认证次数及constructor次数；小型共享/同内容bytes census与hook透明性另做轻量自检。补测工具原生pattern过滤、原matcher透传、既有hex长度观测与异常object/cause/context/suppression均直接核对，并用小样本/foreign pattern独立实查。 |
| PP4 | 本专项核对成本依据和目标身份：A的速度20%/RSS50%，B的20MB/45MB/20MB是尚未实施的建议，不能记为已达成。A逐字节保留 `/1` 时wire降幅必为0；B尚无原型benchmark。具体方案与正确性选择的全面评审应结合 PM 的方案专项结论。 |
| PP5 | review manifest对其受审Git快照逐项匹配；其后仅任务/review/交付和独立核验附件变更，未改变受审测量工具或方案。delivery manifest全部文件hash实核。R01原失败stderr仍在，修复提交 `27280c4…` 只改一份文档的一行统计，原profile独立重算222/222/217，reviewer关闭记录成立。 |

独立复算的关键数值如下（normal direct / normal readback / extraction_mismatch）：

| 指标 | direct | readback | mismatch |
| --- | ---: | ---: | ---: |
| baseline阶段总计 s | 91.921797 | 187.951635 | 88.230747 |
| 完整wire B | 54050313 | 136471701 | 54045042 |
| 进程峰值 KiB | 2859772 | 7327952 | 2850888 |
| outer bytes事件数 | 222 | 222 | 217 |
| outer hex字符 B | 53977248 | 136398636 | 53972674 |
| outer hex占完整wire | 99.8648% | 99.9465% | 99.8661% |
| 全阶段codec disjoint exclusive占比 | 51.2170% | 51.4675% | 51.3732% |
| 原Result unique bytes | 280770 | 577522 | 280770 |
| 原Result logical bytes | 599418 | 1754462 | 599418 |

outer hex的99.9%主要是已编码的下层完整wire再次按bytes转hex、按值展开，不是31份原raw bytes占wire的99.9%。各路径content-unique payload均280746B。shallow和显式roots census不是RSS或全进程对象全集。

W011 build的 `_require_input` 均2次，完整decode均1次；下层W010均2次，W011 build内constructor计数1/2/4/4/3与报告一致。W011认证cumulative中嵌套W010、codec和重建；constructor自身也包含认证，不能相加或换算成无插桩函数耗时。上述约51%的分母是profile函数self-time之和。

额外readback在六路结束后执行，wire/hash/captures/完整结果与baseline一致。65个既有hex调用窗口中5个刷新HWM；event34的118841892字符窗口将HWM升至该记录最终7319108KiB，返回后VmRSS为355960KiB。这只能定位峰值发生的调用窗口，不能把HWM差值当净分配、把多个HWM变化相加、声称已测清regex/native allocator内部组成；direct/mismatch未做此窗口补测。

历史采信范围：通过相同262源/100runtime身份、snapshot、21命令exit0、所有原stdout/stderr hash及完整W011 evidence manifest实核后，采信W011双1605、typing54、构建/双安装。原pytest/typing成功文字另行读取。本次1048项是证据与工具轻量核验，既不是新增产品回归数量，也不是本机性能新样本。W012的一次baseline/独立profile/补测属于有限synthetic调查；巨大wire未提交，本次只核查原生成工具、保留结果与hash，未重新生成wire。更广partial/未知/T05 violation/来源攻击/异常负例仍按W011同源证据采信。

本专项检查脚本的两次初始失败原样保留：attempt01错误假定capture URI均为绝对路径，改为按原input_site解析相对URI；attempt02错误假定runtime manifest键包含 `layauto_v2/` 前缀，改为匹配其真实相对路径表示。两项均是本专项辅助脚本假设修正，未改产品、原测量或被审结论。
