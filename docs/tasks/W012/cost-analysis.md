# P1/P2 成本调查

调查对象是完整公开 Result 组合，不是中立 draft。产品源码完全未改；本报告不宣称性能改善或 PM 验收。执行计划见 [measurement-plan.md](measurement-plan.md)，实现建议见 [implementation-proposal.md](implementation-proposal.md)。

## 身份与原始证据

- PM 准备分支 `f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe`；main 起点 `0a3326aa363477724465886cd05874d0997fba3e`，已含 W011 最终验收。测量工具冻结提交 `cfaf85e195fcbedb99fbd26b19787afb0577862d`，具体工具 hash 见 [tool-identity.json](tool-identity.json)，probe=`321b84da8f8f8c9f2e8abda1b181f3a7ae9481d474643795de452b21a974cd7e`。
- [preflight.json](preflight.json)逐项证明262源/100runtime与W011冻结一致，并校验原snapshot；完整原矩阵证据继续适用。W011已验收双1605、typing54、构建/双安装，本次没有重跑。当前 Python3.12.14、PyYAML6.0.3、pip check通过；16GiB/4CPU、无其他重型进程。
- [selfcheck.json](selfcheck.json)通过，共享对象/独立同内容/逻辑展开及hook透明性均实际检查；初始错误预期和原stderr保留于[selfcheck-attempt01.txt](selfcheck-attempt01.txt)。没有删除产品失败或性能样本。
- 六个fresh进程均串行；每项 `.command.json/.stdout.txt/.stderr.txt/.samples.json` 原位保存。baseline/profile分别采集，不能互作耗时对照；完整wire只保留bytes/hash，避免重复提交巨大wire。输入固定清单可按origin/target逐字节重建mismatch overlay。

## 无插桩完整路径基线

单位：秒；wire为实际B；RSS为整进程KiB。每条仅一次有限synthetic样本，时间不包含后续hash/断言/诊断，峰值不是增量分配。`build合计`包含获取、caller-read及W008–W011全部构造。

| 路径 | 获取 / caller-read | W008 | W009 | W010 | W011 build | 完整encode | 完整decode | build合计 | 阶段总计 | wire B | 峰值RSS KiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| normal direct | 0.707 / — | 0.378 | 0.752 | 11.887 | 32.973 | 1.582 | 43.642 | 46.697 | 91.922 | 54,050,313 | 2,859,772 |
| normal readback | 1.449 / 1.190 | 0.598 | 1.202 | 23.409 | 68.863 | 2.822 | 88.418 | 96.712 | 187.952 | 136,471,701 | 7,327,952 |
| extraction_mismatch | 0.714 / — | 0.380 | 0.613 | 11.241 | 32.316 | 1.393 | 41.574 | 45.264 | 88.231 | 54,045,042 | 2,850,888 |

三者各31份捕获/280,706B，wire/raw分别192.55×、486.17×、192.53×。正常direct的输入URI与历史一致，wire/hash恰与W011一致；readback用了明确的W012 RunRequest，mismatch固定新URI，不能把另两条历史wire差异称为退化或改善。环境/对象保留和计时也不与历史视为严格同条件对照。

完整路径均真实算出36项FIN evaluation、normal MN0=5/MP0=7及全部crossing；mismatch实际4/7，touch FIN保留、恰一个fins_per_finger差异measured4/source5。原40图形/18FIN、8edge/6component、局部T05 pass和独立body事实保留，完整公开decode与原DTO相等。readback attempt/checkpoint不变、unsealed、无terminal。partial/未知、T05 violation、source/target分离、跨捕获/来源/异常等更广负例按同源W011采信；不把本轮三条正常构造扩写为实际运行所有攻击路径。

## Profile 与保留成本

三条profile完整通过，wire/hash及capture清单分别与各自baseline完全相同。原始 `.profile.json` 保留各函数calls、primitive calls、exclusive/cumulative时间及真实wire事件；[cost-summary.json](cost-summary.json)由[summarize.py](summarize.py)重建。插桩使时间增加约2–3倍，以下秒数仅解释profile内部工作，不投射成无插桩函数耗时。

### 1. 原bytes保留与按值重建确实不同

单位B；unique按对象id，content按SHA256+长度；logical按所有引用路径展开。shallow不含实例字典、allocator/native开销，不等于RSS。显式retained_roots census不遍历repository内部存储，不能叫全进程对象全集。

| 原完整Result | unique bytes | content unique bytes | 同内容独立bytes额外量 | logical bytes | SourceFile对象数 | unique对象 / shallow B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| direct | 280,770 | 280,746 | 24 | 599,418 | 31 | 33,810 / 2,240,285 |
| readback | 577,522 | 280,746 | 296,776 | 1,754,462 | 62 | 82,212 / 5,536,112 |
| mismatch | 280,770 | 280,746 | 24 | 599,418 | 31 | 33,807 / 2,240,155 |

完整decode后的direct/mismatch bytes各599,418B、SourceFile各62份，readback bytes1,754,462B、SourceFile186份；按内容唯一仍为280,746B，说明按值恢复确实把共享/相同内容分成了独立副本。恢复图对象/shallow分别169,436/10,831,413B，310,790/20,561,990B，169,393/10,828,978B。这些是实际重复，不可把原共享引用误算成每路径都驻留一份。raw bytes驻留只是不到2MB的量级，不能把GiB级峰值全部归为“保留了31份原捕获”；大量临时序列化/解码分配需另查。

### 2. wire按值展开与外层hex的直接贡献

完整encode阶段，仅取最外层 `ChannelIdentityResult` 的真实 `_wire(bytes)` 事件（不取decode中的重编码流量）：

| 路径 | 外层hex字符B / 实际wire B | 占比 | input完整W010 wire B | semantic完整W007 wire B | value.local wire B |
| --- | ---: | ---: | ---: | ---: | ---: |
| direct | 53,977,248 / 54,050,313 | 99.8648% | 22,789,218 | 2,622,874 | 1,198,095 |
| readback | 136,398,636 / 136,471,701 | 99.9465% | 59,420,946 | 7,201,840 | 1,198,095 |
| mismatch | 53,972,674 / 54,045,042 | 99.8661% | 22,789,282 | 2,622,882 | 1,198,095 |

外层bytes事件数依次为222 / 222 / 217，上表三个大分支各按原长度×2嵌入；余下还包括完整completed、参数、typed refs等。direct的input单分支占最终wire约84.3%，readback约87.1%。外层非hex部分仅约73KB。但hex里大部分是**下层已序列化的完整语义/捕获/来源结构**，不是31份原数据直接变hex；不能将99.9%解释成“原bytes占99.9%”。各层 `_pack` 把完整下层wire作为bytes，`domain.codec._wire`再转hex，下一层继续按值重复，Python共享对象不会自动在wire中去重。

只有去掉最外层hex的理想账面反事实，且不计新格式开销时，约能少26.99MB/68.20MB/26.99MB；它不是新codec的实测结果，也还保留所有更深层重复。要实质减少wire字节，必须改变表示或另增格式；保持 `/1` 逐字节相同时 wire 降幅必为0。

### 3. 公开constructor重复认证的调用链与时间

下面为W011 build阶段：

| 路径 | profile build wall | W011 `_require_input` calls / cumulative | 内含W010 `_require_input` calls / cumulative | domain.codec exclusive / 全部函数exclusive总计 |
| --- | ---: | ---: | ---: | ---: |
| direct | 104.003 | 2 / 95.354 | 2 / 35.598 | 53.564 / 103.865（51.57%） |
| readback | 178.983 | 2 / 167.851 | 2 / 67.623 | 92.338 / 178.834（51.63%） |
| mismatch | 105.760 | 2 / 96.759 | 2 / 36.234 | 54.799 / 105.616（51.88%） |

W011 `_require_input`累计约占本阶段92–94%，自身exclusive却仅约微秒至毫秒；成本在完整下层codec/reconstruction。下层W010累计包含在上层数字内，**不能相加**。每次本阶段实际构造ChannelIdentityResult1次、LocalConnectivityResult2次、EffectiveGeometryResult4次、GeometryResult4次，ChannelIdentityDraft3次。W011 constructor另外占累计53.342/92.150/55.487秒，其中又包含上述认证和重建，不能当另一份独立成本。

完整decode阶段，W011 `_require_input`实际各1次（累计46.592/87.108/49.217秒），W010各2次、W009各4次，公开constructors同样触发完整重建。decode中还存在canonical重编码检查。domain.codec的disjoint exclusive为65.163/125.639、114.281/223.340、68.656/132.597秒（约51–52%）；这组分母是profile函数self-time总计，不是receipt wall。direct build的 `freeze` alone实际17,423,559次调用、18.629秒exclusive，FrozenMap构造4,894,594次、8.778秒exclusive；其cumulative互相嵌套不能相加。codec以外的Mapping迭代、isinstance、正则、JSON和dataclass等工作也在原数据中，不说全部成本属于一个函数。

hook本身在W011 build各占exclusive1.540/2.533/1.589秒、decode1.668/3.084/1.709秒，另有cProfile分散开销；这些不是产品瓶颈。所有wrapper只观测既有返回长度/类型，未额外encode/digest大对象。不能把profile相对baseline的耗时增加当产品退化。

### 4. 峰值内存的限定补测

额外完整readback在六条结束后串行完成，工具[自检](memory-probe-selfcheck.json)、[命令/原输出](memory-profile.command.json)、[调用事件](memory-profile-events.json)、[完整结果](memory-profile-normal-readback.json)全部保存；原probe未改。完整来源/36个evaluation/局部图/body/attempt断言通过，wire仍为136,471,701B、SHA256与baseline相同。该次decode148.115s是诊断运行，受hook/环境波动影响，不替换88.418s的baseline。

只观察原 `re.fullmatch(r'(?:[0-9a-f]{2})*', raw)` 对既有大hex原生str的调用，共65次≥1MB事件，5次刷新进程HWM。代表窗口：

| event（0-based） | 既有hex字符数 | 调用前RSS KiB | 调用后RSS KiB | 调用前HWM KiB | 调用后HWM KiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 27,882,860 | 141,284 | 141,292 | 141,216 | 1,774,880 |
| 10 | 57,757,844 | 176,780 | 197,704 | 1,812,624 | 3,581,872 |
| 34 | 118,841,892 | 340,640 | 355,960 | 3,589,092 | 7,319,108 |

event34对应外层input的59,420,946B下层wire转hex；它将HWM刷新至该完整进程最终峰值7,319,108KiB。调用返回后RSS约348MiB，不能把HWM当仍然驻留的bytes或净分配；也不把5次HWM变化相加。这里没有额外encode/复制大参数，除观测元数据外窗口执行的是原matcher。因此可以把这个实际readback的最高瞬时峰值定位到既有hex校验调用窗口；具体内部allocator/regex引擎栈的逐项分配没有测量，不声称已证明全部native内存组成。direct/mismatch没有另跑同样窗口诊断，不杜撰其函数级峰值数字。

这把内存优先项收敛到 `domain.codec._decode` 的重复分组正则，再处理层层hex/JSON/FrozenMap临时表示；原raw bytes去重只会处理MB以内到约1.8MB的已测payload重复，不能独自解决该GiB峰值。

## 数值目标建议与限制

建议顺序见[具体方案](implementation-proposal.md)：先降低既有 `/1` 的瞬时序列化/解码空间及公共codec重复拷贝，保留公开验证；再由PM/用户决定新的自包含表格式。原bytes去重作为次要内存收益，不把它当GiB峰值的单一解法。认证函数占比高，但不授权删除认证或改异常合同。

兼容工作包A的速度目标建议：同条件三次中位阶段总计至少降低20%，direct≤73.5s、readback≤150.3s、mismatch≤70.5s；任何单路径退化需单列，不能用平均掩盖。依据是三个profile的domain.codec disjoint self-time均约52%（全部阶段合并仍约51%）；若能消除其中约40%的重复工作，账面上约有20%的整体空间，但该换算受cProfile扰动、非codec开销及实现复杂度限制，**不是收益预测或已达成结果**。wire必须逐字节保持三条既有hash（0字节降幅）。

RSS目标建议为各路径峰值至少降低50%：direct≤1,429,886KiB、readback≤3,663,976KiB、mismatch≤1,425,444KiB。依据是readback在仅约340MiB当前RSS时，hex matcher窗口将峰值刷新到约6.98GiB；有明确的瞬时空间可调查，50%作为兼容优化可行性门建议。其他路径共用相同decoder但未做函数窗口补测；这些门不是已验证降幅，若实现后出现其他峰值须保留并重新审查，不宣称生产/最大输入资源上界。

可选格式B的wire目标建议：direct/mismatch≤20,000,000B、readback≤45,000,000B（约63%/67%减少）；它比仅去掉外层hex的账面反事实更进一步，需减少更深的按值展开/重复证据。结构和实测尺寸支持调查这一路径，但没有原型benchmark，若用户批准格式方向，仍须在实施前细化schema/兼容/内容身份并用完整路径验证可行性。不能以移走捕获、外部repo解析、只编码draft、少比字段或热缓存达标。

所有数值是交PM的目标建议，尚未批准、未实施、未形成验收承诺。未来优化实施开发先新增/受影响，最终冻结双全量/typing/构建和安装；还需相同URI/RunRequest/cache/GC及保留roots的前后完整三路测量，独立正确性/性能review。现在只交调查和方案，到PM接收停止。
