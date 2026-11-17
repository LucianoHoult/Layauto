# W016 恢复实施记录

当前以[交付记录](delivery.md)与completed冻结为准：298文件SHA-256
`f99498abc0877bb918d7de88d66a5eda5d5591d41f8ce8102b04edc14826c052`。
代码/接口/四路兼容及R03–R10独立复核完成，双3.10/3.12完整各1953项及各3项fixture补充均通过。以下按实际顺序保留阶段记录；
其中旧冻结的“将启动/待完成”及1954项是当时描述，不能用作当前完成结论。
当前完整tests实际collection为1956（unit/contracts1953，加fixture_support3），两解释器节点一致。

恢复提交与远端：`6ca7b16cff0f953f9e7eacc834f88ac28e70abb6`，原分支
`codex/w016-single-cell-analysis`，启动工作区干净，仅根 AGENTS 适用。
已读取 resume-prompt 和 PM 资源决定，纯体积优化后置，不做第三轮表示优化。

本轮实际文件新增：公开 analysis.py、normalization/analysis.py，tests/support/analysis_inputs.py，
tests/unit/test_analysis_api.py、tests/contracts/test_analysis_body_parity.py；
现有 domain.analysis 增加只读结果/facet/selection/terminal view；tech.analysis_schema增加manual；
reader增加独立外部获取和binding alias固定；receipt replay区分lookup与实际visited。
terminal_relations在旧strict wrapper下提取TerminalOperands纯定位，旧DTO/wire不改。
README与typing清单同步。

认证：实际获取本地闭包与raw各一次 → immutable Evidence → Receipt完整重parse bytes；
独立所选body/manual获取一次、固定其来源绑定alias → 纯normalization重新解析/绑定/评估。
本地图不union外部图形；source参数比较不构target。report保留全部facet与诊断，没有decoder。
预期InputError/各owner typed problem转换为原code/ref的诊断；未知异常/interrupt传播。

迭代测试：先新增公开API及其来源/状态/手算/纯度范围，再旧共享算法受影响回归；
独立review与候选完整wire parity串行，复用原normal-direct唯一基线。
早期三case整体探针均可运行；正式资源分阶段/计数证据继续补充。
最终矩阵在独立review修正后的源码/测试/config冻结时再执行，不能采信旧58项当新功能通过。

原失败保留：初次新API测试因pytest保留参数名request收集失败（已改名），
partial FIN初测因top aggregation将原unsupported category当顶层unsupported而失败（已修正：
有诊断draft的局部计算error保留原category/code/ref但severity error→rejected）。
原基线和原资源门/失败证据均不覆盖。

新增真实文件验证覆盖：无body 5/7及六端；body同local graph独立八端；缺文件、syntax、hash、top、
role、未知URI、未知字段、unit及现有错误body链；manual绑定/日期/重复/伪assurance；
未来selector无IO；FIN4对5、partial FIN、实际GDS+query手算40/24/16和overlap8；
请求边界、完整捕获一次及纯计算无IO、补资料显式重调用、旧codec/consumer互拒、native存储防伪。
source FIN mismatch的finding定位到实际declared参数并保留channel/binding refs。

发现并修正的另一个验证输入问题：A2旧新对照临时目录保留旧normalized cache；新header身份导致
NormalizedCacheMismatch，属正确拒绝。显式迁移helper现在将原cache bytes保存在original-normalized，
不把旧cache当新header解析结果；原失败body-parity.attempt01保留，固定fixture和答案不改。

调度说明：A2旧链对照一次26秒尝试与已启动的baseline mismatch有短暂重叠，记录为迭代调度，
不用于新API资源测量；其他大型验证继续协调串行。最终矩阵须在独立review修正后冻结源执行。

冻结标识：298项源码/测试/config，manifest
`evidence/resumed/final-source-identity.json` SHA-256
`af23726d482621502c322ba207b610b49bf10881aaf856f55b208009e5d8bd50`。
双3.10.22/3.12.14 mypy各75源通过；双构建（显式安装setuptools/wheel，--no-isolation）通过，
原输出和命令/时间/hash在 `evidence/resumed/final/`，wheel/sdist身份在build-artifacts.json。
虚拟环境、build和安装树均在/tmp，不作为仓库交付物。

复用/补验原则：原58项仅原检查点证据；本轮新代码按最终manifest重验。两版原codec逻辑未改，
候选旧兼容完整构造DTO和公开encode与已decode的baseline逐bytes比较，保存长度/hash与比较结果，
不重复落第二份相等大wire或再decode同一已证相等wire；最终codec回归仍须完整跑。

资源口径延续未压缩UTF-8完整报告，不单独压缩或删诊断。新测试迁移使用实际临时文件和compact
manifest/header，早期三case capture为42395/45202/42395 bytes，较原W015 candidate输入的
44873 bytes不同；路径/JSON格式/新synthetic身份也不同，不能把倍率变化当同输入退化。
早期完整公开report为235792/259620/235838 bytes。body增加的报告来自独立路径、规则审计、
外部来源和B端支持，本地图保持原值；计数确认top body evaluator只调用一次。
所有当前stage/整体/HWM/bytes以及profiled neutral构造次数按各自原输出保留，
不将有profile运行的约11.5秒和无profile的约2.7秒混为同一性能样本。

独立review补出R06：原manual只有文档根ref，未显式给出逐字段位置。现保留原声明文档并补
作者/日期/cell/hint、两个source的URI/hash、每条assertion对象及三个字段的真实SourceRef，
不伪造原文/scope。实际双assertion测试与独立反例已通过，声明不补observed/parent。
新的交付冻结298文件为 `evidence/resumed/delivery-source-identity.json`，SHA
`a306a2ae0f5aee5c37734764378520f927846bcb7e08b9e97ce88245c7e01a6e`。
原af23726d冻结/59项/A2/构建/安装/资源原输出完整保留；最终双全量尚未启动，
在新冻结重验manual受影响定向、双typing/build/安装含manual smoke和三case资源。

最终矩阵前还发现R07：Python Path中非法surrogate导致UnicodeEncodeError，已在请求边界只捕获
明确的UTF-8编码错误，返回located InvalidAnalysisRequest，未知异常继续传播；根/相对/目录/
不存在路径仍保持各自原因。实际原失败request-unicode.initial.json、6项修后测试与独立高/低
surrogate+合法中文路径复核保留。新release冻结298文件，
`evidence/resumed/release-source-identity.json` SHA
`dae9e716acb4e4f947db12779362c677615cdc12c03c0852fbf9cde3a69a977e`。

相对a306只新facade请求预检与现有request测试参数变，旧producer/wrapper/codec及配置均逐字节
相同。normal-direct候选已在a306全身份稳定时完成98.94秒的完整DTO/公开wire精确比较，按实际
影响身份采信，不因本次仅新入口请求预检重跑大wire。随后readback候选因新冻结调整被停止，
保留exit-15和调度记录，不作为产品失败；其余三路在release冻结重新执行。

所有四路candidate完成逐bytes精确DTO/wire比较通过后，独立review无未关闭must。
补充新入口真实输入探针确认wrongtype/ambiguous body原错误及local保留、missing seed局部依赖、
100nm² unmatched与40nm² gap、SREF flat限制原unsupported位置；源未改变。
Python3.12完整1954项矩阵已在release冻结启动，之后串行3.10。

首轮完整3.12矩阵在488passed时发现2项真实失败，181.86秒后主动中断（非完整通过）：
既有W005/W006硬边界AST测试发现domain.analysis导入pathlib，初始检查点带入此问题。
原stdout完整失败及中断sidecar在release/；一次按默认collection顺序反推失败节点的heuristic
误指W008，已保留纠正说明，权威为原traceback两个AST失败，不冒称W008回归。
SIGINT同时中断driver及pytest，未生成正常完成metadata，sidecar明确记130及原hash。

R08修正：冻结AnalysisRequest移到其唯一公开facade（持Path），domain只留中立Evidence/view，
不放宽任何旧依赖测试。原两项+6请求测试及独立真实无body调用/冻结性/错误定位通过。
最终新冻结298文件为verified-source-identity.json，SHA
`73cb080765e2e317f2f54269f8cd306ed5e352c8c21dd2ae575f8920db54fa7b`；
双typing/build/资源/clean安装在新冻结重验。旧四路parity相关producer/wrapper/codec及配置逐字节
未变且不import两新analysis模块，独立按相关身份采信；完整双全量必须重新执行。
下一轮采用--maxfail=1，仅失败时早停，若全通过仍执行所有1954项；不削减正确性或矩阵。


## 最终工程验证闭合

completed冻结298文件（SHA见首段）保持不变，双长矩阵串行正常exit0：
3.10.22为1953 passed/10798.06秒，3.12.14为1953 passed/7745.36秒；
双fixture-support另各3 passed及8 subtests passed，精确补齐正式tests全集1956节点。
根默认多收的W011历史docs插件demo不属正式产品矩阵，节点差集依据保存在collection-scope。
双typing各75源、双build、双clean安装源码外5case smoke和三API资源/独立profile计数均完成。
[最终执行核对](evidence/resumed/completed-validation-summary.json)核11个exit0命令、
原输出hash及当前全部298项字节一致；不因最终文档补记重跑已通过矩阵或大wire。

完整A1–A8依据、按相关源身份采信的四路旧DTO/wire parity、原失败/修正及生产未覆盖范围
见[交付记录](delivery.md)和独立review。工程交付交PM，不改变PM阶段，不自行验收或合main。
