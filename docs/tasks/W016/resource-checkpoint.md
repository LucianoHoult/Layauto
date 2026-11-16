# W016 资源门恢复点（未完成交付）

基线及已获取远端：`efc881d461ce2c87370f6df402ac50ae43c094e8`；
工作区 `/workspace/Layauto`，分支 `codex/w016-single-cell-analysis`。
启动无既有改动。首次资源暂停时未提交；本轮 PM 已明确授权将相关实现、测试和证据作为
**未完成检查点**提交推送原分支，暂不扩展功能。检查点不等于完整实现、最终 review 或验收；
PM 阶段/current-work/要求和资源门不修改，不合 main。完整交接 SHA 由提交后远端核对提供。

## 已做与暂停原因

已实施独立 manifest/header schema、本地实际文件捕获、中立 Evidence 与全 bytes 重parse Receipt，
source-only identity operands、中立 geometry/FIN 链、新 annotation binding/draft、共享 annotation
算法与一致性校验；body pure evaluator 仅完成提取，尚未接入新认证 wrapper。
独立 reviewer 已发现并复核修正存储防伪问题，完整实现 review **未完成**。

最早内部链实际运行到 source/drawn/effective/local/channel/annotation，正常 FIN 5/7，
annotation 无 issues、6 components；没有构造旧 NormalizationInput、target 或完整 Result。
这不是公开 `analyze_cell`，不能把内部链标作 A1 完成。

W016/W015 要求去重 report >2× capture 时解释构成并交 PM、暂停扩包/最终矩阵。
内部报告原型实测触发该门；随后两次定向缩减仍超门：

| 版本 / 原日志 | capture bytes | report bytes | report/capture | 对象数 | 阶段耗时合计 s | report阶段 s | 进程峰值 KiB（bytes） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [缩减前](evidence/local-probe-report.stdout.txt) | 44873 | 262231 | 5.843848 | 2021 | 2.517866 | 0.038481 | 26112（26738688） |
| [第一轮：Evidence payload改digest/source](evidence/local-probe-report-reduced.stdout.txt) | 44873 | 248542 | 5.538787 | 1956 | 2.180575 | 0.024013 | 24724（25317376） |
| [第二轮：SourceRef改capture索引](evidence/local-probe-report-sources.stdout.txt) | 44873 | 235613 | 5.250663 | 1869 | 2.058048 | 0.025801 | 24732（25325568） |

第一轮减少13689 bytes，第二轮减少12929 bytes，累计减少26618 bytes（原报告的10.15%）。
这是同一synthetic输入的三次增量实测，不是控制变量性能基准；当时包含防伪修正及主机负载差异，
不能将耗时/HWM变化归因于编码修改。峰值是Linux `ru_maxrss`进程累计值，不是report增量分配。
阶段合计从获取开始到report计时点，含中间日志/探针打印开销，不含导入和末尾文件写入；
不等于公开API端到端耗时。单次观测没有均值/置信区间；加profile计数的测量不混入此表。
逐阶段原值与复算保存在[checkpoint-metrics.json](evidence/checkpoint-metrics.json)。

### 分母、编码及去重口径

- capture为23个实际获取文件的`len(SourceFile.data)`去重之和：44873 bytes。包含manifest、新header、GDS/source CDL、tech bundle及六owner、limitations、requests/dialect和raw captures；不按facet重复累计，不含不存在的target/export/validation/body/manual文件，不是Python对象占用或压缩大小。
- report为`json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False)`输出的UTF-8字节数，无缩进、无末尾LF、未压缩。最终实物为235613 bytes，SHA-256为`958b5c97685f49c511720e6f019a61fb09295551b0df39669f8b96624b2da554`；不能用磁盘block大小、gzip后大小或repr字符数代替。
- 通用复合值按渲染后的完整结构去重，`objects`保存一次，facet和子对象用报告内整数`ref`连接。保留真实typed content refs；这些整数地址不是受信receipt/ref。raw bytes只保留hash/长度；SourceFile只列URI/hash/长度；第二轮SourceRef使用capture索引及非空位置字段。解析Evidence只列kind/payload digest/sources；已有实算facet仍可展开，报告没有decoder。
- 这是**结构去重**，不是全部语义/词元去重。FrozenMap中的`path/sha256/lexeme`来源位置仍可重复；SourceRef/EvidenceRecord特殊分支直接内联，schema字段名/版本和值字符串没有全局字典。

报告不含 raw bytes，无旧多 Result 嵌套；所有复合值以短整数地址去重，真实 content refs 保留。
[完整报告](evidence/local-diagnostic.json)、[分组构成](evidence/report-composition.json)、
[首测](evidence/local-probe-report.stdout.txt)、[最后未加计数测量](evidence/local-probe-report-sources.stdout.txt)
及[构造计数](evidence/local-probe-counted.stdout.txt)为实际输出。前两版 encoder 保留在 evidence。

首测阶段秒数：获取0.208、认证0.252、source/identity0.015、drawn0.069、effective0.105、
local0.348、channel0.440；后续 annotation 约0.789、report0.038，HWM约26MiB。
这些是不同增量探针的阶段，不冒充一次完整 API 计时。当前逐阶段原值以上述原输出为准；
`sys.setprofile`计数测量单独保留，不与无计数墙钟混用。
一次获取、一次 Receipt 全字节重parse：GDS/CDL/query各2 parse；中立顶层 builder各1。
内部完整一致性重建另有 geometry2279/channel2034/net_annotation1448 等构造，详计数输出；
generator的56次call含resume，**不是56次认证**。尚无有body/FIN mismatch新链三case矩阵。

调用图：实际文件获取 → 新schema/完整本地closure/raw解析 → Evidence →
Receipt从保留bytes重parse → source/identity → layout/partition/occupancy → effective → local →
channel/FIN → 新annotation binding/完整overlay与重构验证 → 诊断DAG（无decoder）。

### 当前报告构成与可削减部分

以下是对已保存报告做只读UTF-8词元核算，没有导入产品或重跑链。
[脚本](evidence/checkpoint_metrics.py)逐token分类并断言各项合计恰为235613 bytes；
[完整统计](evidence/checkpoint-metrics.json)保留规则、原值与重复字符串样本。
这是表示层的互斥账目，**不是“只有事实值才必要”或可直接删除字节的估计**：
字段名、单位、位置、关联和类型也是正确解释事实所必需，只可等义编码。

| 类别 | bytes | 占整个report | 性质及处理 |
| --- | ---: | ---: | --- |
| 事实scalar值（source声明及派生事实） | 16204 | 6.88% | 精确坐标/计量/参数/状态等，保留；关联结构另计在下面 |
| 来源/provenance值 | 37892 | 16.08% | 包含必要来源，也包含重复路径/hash/lexeme；不能整体删除 |
| typed identity/ref值 | 11851 | 5.03% | 真实对象身份及绑定，必须可还原；可调查同值字典 |
| DAG链接`{ref:n}`完整token | 38047 | 16.15% | 共享对象的必要连接，不是重复嵌套对象；可用有明确schema的紧凑地址表示 |
| JSON字段名、键值分隔/容器语法 | 111202 | 47.20% | 重复字段名是主要展示开销；语法不能全部消失，宜按类型共享字段表 |
| 展示type/schema_version值 | 20417 | 8.67% | 每行重复类型/版本；可一次声明类型/版本再逐行引用 |
| **合计** | **235613** | **100%（舍入前）** | 仍超2倍门；不把此分类当新的验收口径 |

其中来源值内，重复字符串首次出现后的编码总量为**30710 bytes**（与上表重叠，不能相加）。
它是未计字典/索引成本的gross上限；包含重复路径、hash和lexeme等，不代表30710 bytes都能消除。
新的来源位置表应把capture角色/URI/hash与字段/record/lexeme位置分开索引，精确保留每个反向引用。
[旧按对象分组](evidence/report-composition.json)仍保留：来源字段map25747、drawn13756、
classification11518、FIN evaluation10230、derived provenance9581 bytes；这些分组含各自语法，
不能与上表累加。

另按root可达性对对象表做互斥分摊，避免把共享geometry/source重复归到每个facet：

| 存储归属 | objects | bytes | 占整个report |
| --- | ---: | ---: | ---: |
| 多facet共享，包括source/drawn/effective/local链 | 920 | 99090 | 42.06% |
| annotation专属 | 729 | 97206 | 41.26% |
| channel_fin专属 | 220 | 33761 | 14.33% |
| 顶层capture表/roots及外层JSON语法 | — | 5556 | 2.36% |

没有不可达对象。1869行对象表的完整编码**完全相同重复行=0**，未发现完整旧Result链递归复制；
这是已完成的结构去重效果。它不证明所有inline来源描述、跨类型的相同语义或字符串均无重复。
因此不能将共享的99090 bytes说成“重复嵌套对象可删”，也不能因重复行为零就停止来源/表示检查。

### 推荐处理方案（建议，未实施或批准扩包）

1. 先设计诊断专用字段表：每种record的字段名/版本声明一次，行只保存typed值与引用。优先处理占55.86%的键/语法及type/version开销，并替换反复出现的`{ref:n}`包装。引用必须仍可定位到完整行；不是只显示摘要或隐藏未执行facet。
2. 来源集中表覆盖现有FrozenMap位置与inline来源描述，而不只处理SourceRef对象。capture仍保留首次URI、hash、角色与alias事实；位置保留field/record/byte/line/token、lexeme及derived来源。保留raw在receipt中的单份实际bytes和完整重parse；report索引不能替代认证。
3. 继续按owner共享geometry/topology/annotation对象，检查跨类型语义重复，先提供逐项等义映射和独立反例再消除；不通过复制旧Result、删除完整capture或跳过中立构造验证简化成本。旧DTO/wire不能随报告优化改版，新report仍只是不能回灌受信receipt的诊断view。
4. 必须保留每个drawn/unknown/C1/C2记录、exact有效区域、所有node/edge/component及局部规则、每FIN qualification/差异/未知原因、source全部参数与ordered terminals、全部annotationtargets/fragments/coverage/gap/conflict/unmatched/classification以及可追溯来源。后续body/manual/parent/status/dependency各scope同样不能被压成一个pass/fail。
5. 等义方案经PM复核后才做下一轮小型测量，沿用未压缩总JSON字节口径。当前2倍上限为89746 bytes，仍超145867 bytes；上面的gross展示/重复量不构成可达性保证。若专用投影仍不能满足门，交PM讨论预算/分段呈现合同；分段也须统计全部诊断总量，不能只计首屏/摘要，不自行调整门或以gzip通过。不复活W012 A2。

本轮只补统计与检查点交接，未做上述编码改造，不扩body/manual/terminal/API。

## 验证与未完成范围

本次实跑：

- `/tmp/w016-py312/bin/python -m pytest tests/unit/test_analysis_foundation.py tests/unit/test_w013_net_annotation.py tests/contracts/test_w007_inputs.py -q`：58 passed，23.27s，见[原输出](evidence/targeted.attempt01.txt)。新测试从实际捕获显式迁移到临时文件、没有target/body/policy文件，覆盖重parse无IO、补资料新获取、payload/raw/alias/mutable/extra-field反例及新旧header互拒。
- 原typing配置 `python -m mypy`通过；7个新模块显式typing通过。原两次typing失败及修后输出均保留。
- 独立 review 的旧接口基线完整DTO/wire/roundtrip探针另见[review](independent-review.md)；尚未完成两侧parity，不把baseline单侧通过当兼容通过。
- Python3.12.14环境已在`/tmp/w016-py312`安装；3.10.22解释器已下载，尚未运行最终矩阵。

按身份采信：只采信已接收W015设计合同与历史边界，不用历史W014测试冒记本次兼容。
未覆盖：A1–A8整体、公开API及facet/status聚合、external/manual/terminals、三case资源、
完整alias/forged refs矩阵、双侧旧wire parity、独立最终review、双3.10/3.12全量/build/clean安装。
真实PDK/工具/生产环境始终未验证。无baseline/no_change/terminal/修改/发布许可。

恢复：先读此文件、独立review和 source-identity.json，核工作区身份；PM资源复核后继续报告
专用投影，再完成剩余实现、A1–A8与review及最终矩阵。源码/测试/config再变应补受影响检查，
最终交付须新冻结双矩阵；本轮没有可复用的最终矩阵。

环境过程：普通沙箱首次fetch因proxy不可达失败，获环境网络权限后fetch成功且SHA匹配。
系统Python最初无mypy；在独立`/tmp/w016-py312`安装dev依赖后实跑typing。
该uv venv无pip，`pip freeze`失败；普通沙箱`uv pip freeze`又因只读cache失败；最终使用
同一解释器`importlib.metadata`保存[实际依赖版本](evidence/dependencies.txt)，未把失败当安装/验证成功。


## 本轮检查点封包与验证复用

本轮新增实跑仅`python docs/tasks/W016/evidence/checkpoint_metrics.py`（现有235613-byte报告只读统计）、报告长度/hash/比例复算、293源码/测试/config逐文件身份核对、文档链接与`git diff --check`。未改变产品源码/正式测试/config；据同一source manifest采信此前58项定向测试、两组mypy及R01/R02独立修后复核。不重复最终矩阵或旧重链。

已测路径只有synthetic正常无body内部六facet链及上述定向/反例、旧正常direct单侧baseline。尚缺有body正常、无body FIN4对5的新完整资源路径、public API与错误/status汇总、manual/terminal、旧readback/mismatch/wrong-body与候选两侧parity及A8最终矩阵。这些小输入数字不代表最大输入、一般层级、生产PDK/方言/EDA、部署主机性能、完整单cell分析结果大小，也不证明时间/HWM相对旧W014改善；旧七阶段encode/decode不是同口径reference。

封包保留相关源码/测试、两处独立防伪复核、原失败日志、原encoder版本、资源探针及实际报告。旧baseline唯一压缩DTO/wire快照约5.1MiB保留：它们支持未来同URI完整字节比较，避免重跑已耗时200秒以上的单侧捕获，hash本身不能代替精确比较；不是新的大wire重复封包。未收环境/解释器、缓存、bytecode、egg-info、临时安装树或失败尝试的重复大快照。所有checks仅支持这个未完成检查点，提交推送不代表A1–A8通过或验收。
