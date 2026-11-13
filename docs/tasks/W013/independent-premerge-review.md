# W013 合并前独立复核

2026-11-13，独立新会话 reviewer `/root`；专项 `/root/coverage_review`、
`/root/neutral_codec_review`、`/root/binding_review`、`/root/evidence_review`。
本会话及专项均未参与 W013 设计、产品实现或正式测试编写。主 reviewer 汇总实际代码、
原合同、独立反例及公开路径结果；PM receipt 只作为待核材料，不代替产品判断。

**结论：可进入 PM 集成及组合验证。未发现新的阻塞项，必须修正项 0。**
判断仅适用于当前 synthetic、exact rectangle、local/source-evidence 草稿范围；不是 PM
验收、main 已集成、完整 M1、外部 body/U06 或真实 EDA/LVS 通过。

## 版本与审查边界

| 身份 | 完整值 |
| --- | --- |
| 实际 base / 远端 main | `d6182fe6893c26490f9d58c6b808a5ce9910384b` |
| 恢复及受审 PM head | `f31df3f3e6cd5df7ecef2e1f91977c3b68a9fac4` |
| 原产品交付 | `63a0962f1b56655f234140822bffa8f56b7bb15f` |
| 最终产品冻结 | `2a45938aba8e751183d472d660a1ab66a1063636` |
| 273 项 source_id | `2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278` |

从 `/workspace/Layauto` 原 `work@d6182fe`、干净工作区恢复指定远端分支；实际 fetch 和
ls-remote 核到上述完整 head/main。读取根 AGENTS、README、协作与环境规范；新分支扫描
仅根 AGENTS 适用。独立审查 base→head 全部 13 条产品/测试/config 路径，以及 W007 identity、
W008 capture/geometry、W009 region、W010 graph/codec 的生产者与消费者合同。六个新增
runtime 模块、公开入口、typing 范围和 W007 精确依赖 guard 均纳入。

读取当前任务 A1–A8/PM1、P01、方案及方案 review、完整 code-review、handoff-scope-audit、
resource-summary、R2 最终证据与采信链；对照 architecture §3.3、3.5–3.8、5.3–5.9、
11.2/11.5/11.9/11.15、MR-020/MR-034 及现行 spec/oracle/independent local answer。
旧失败、修后记录及历史引用补正保留原身份，未把历史中间状态当作当前未关闭 finding。

独立核 273 项实际路径集合（含相关 tracked/untracked 选择）、磁盘字节、冻结/交付/PM-head
Git 对象和源码 tar 全部相同；106 runtime 与两包内容相同。复核期间新增的 `work/` 只含
审查脚本、输出和草稿，不在受测产品选择中；最终只归档必要证据并追加 reviewer 区。
未改产品、正式测试、fixture、旧报告/codec、PM 段或 current-work。

## A1–A8 独立判断

| 要求 | 实际检查与独立正确性依据 | 判断 |
| --- | --- | --- |
| A1 同源/身份 | 手读真实 NET NAMES+nXref，reader→W007 得到四组 n_a/A/1、n_y/Y/2、n_lo/VSS/3、n_hi/VDD/4 及 8 seeds。逐审原 provenance、QueryKey、NetId 与完整 W010→W008 capture 认证；保留原 bytes/hash 的 run/database/top 三字段篡改经实际 W013 入口拒绝。007 按 P01 为两级拒绝反例，旧 parser/QueryKey 无改动 | 当前授权子集满足 |
| A2 精确区域 | 审 Fraction 分区、union/difference、完整 evidence 签名与 target/region 身份。独立格集合 768 项、带孔 target/重复 occupant 的 40 格验证覆盖、冲突和全部来源；边/点零面积、部分覆盖、同网重复及 sub-nm 精确值无整 shape/cell 过标 | 满足 |
| A3 本地分量 | 独立 current local oracle/raw 算术与真实公开输出共同确认 14 nodes/8 edges/6 components=4 关联+2 unknown BODY。cut 专例仍为同 A 标签的三个物理分量、0 边；derive 只读原 topology，直接 fragment 与 component 关联分开，不造边 | 满足 |
| A4 缺口/质量 | 正常分母为 14 targets 的 record 多重集面积 35090nm²，直接覆盖 3170、未覆盖 31920；POLY720/LI1110/M1 1340。OD 四端子及 BN/BP 无直接证据，MARK25 为非导体。审 trim/unmatched/unsupported/conflict 分列与完整分类。approximate_bbox/untrimmed 在现行上游即拒绝，不宣称 W013 已支持其空间匹配；非零 tolerance/不支持 trim 不升级为 exact | 当前子集满足，限制显式 |
| A5 DTO/codec | 审原 storage guard、native scalar/Fraction、字段/来源闭合、owner、全部 contributor、分类及两级认证。独立 neutral 12 类拒绝+正常 roundtrip/DAG、6 项异常链；真实 Result roundtrip、canonical 派生字段篡改拒绝和四公开边界×四异常类型保真。完整旧 W010 Value 一次，恢复原 bytes 走旧 public decoder，旧 wire/ref/认证代码未改 | 满足；CR-01–03 关闭仍成立 |
| A6 有效性/owner | binding/target 绑定 local/effective/layout/unit/partition、source/tech/input/run，保留完整 ContactNode→ExactRegion，而非任意 shape 摘要。固定 source_evidence/local；geometry/operator 改变使 region/target 身份失效，captured 重建比较全部输出。外部 body 仅原 evidence 透传，无 baseline/terminal/publication 或新 LVS 保证 | 满足任务边界 |
| A7 成本 | 独立核 resource04 原 source6463…→R2 唯一 guard-test delta、runtime/config/input/probe 一致。真实 direct 再观察 1/1/2 次 W010 public decode；wire23104092B、旧输入22789218B、新增314874B，与原结构相同，W011 Result 零份。完整认证成本仍存在，inclusive 计时不相加，不作跨环境提速结论 | 无新增资源阻塞 |
| A8 工程/review | 独立 59 项原证据审计：273 源、81 evidence、21 命令、双1731/双typing60、两包106 runtime、双 clean 安装三路 smoke、环境/工具/输入链闭合；本轮另有独立数学/来源/攻击和真实公开路径。首次失败/受控停止不计通过，不重复完整矩阵 | 可交 PM 实际集成验证 |

## 关键必须项的重新核查

CR-01 的三类 owner 一致性均在当前代码验证：topology 单一 local operator、node 与所属
component owner 一致、全部 target region 共用有效算子。CR-02 在复制/编码前检查原
FrozenMap backing、tuple entry/唯一 native key、native 叶、规范 Fraction、cycle 与
value-only 上下文；独立探针同时验证合法共享 immutable DAG 和跨上下文攻击。
CR-03 核 target_conductor 分类与 node/target 一致，并将全部 region contributors 闭合到
完整 drawn 表，继续检查 LI→CUT、OD→POLY 角色。原失败和修正不改写，本轮无重开依据。

保留 W007 guard 的 actual AST allowance 另以 18 种导入组合检验：只放行
`normalization/net_annotation.py`、`net_annotation_codec.py` 的
`from layauto_v2.state.annotation import AnnotationDraft`。额外 symbol、其它模块/文件、
普通 import、mutable/publication 不放行；没有通过宽泛 whitelist 消除首轮架构失败。

新增来源攻击曾暴露需要区分的上游边界：单独 W007 semantic adapter 接受同步篡改的 header
身份字段，而 W008 从原 captured bytes 重新解析 header 后拒绝。为避免只凭静态调用链推断，
主 reviewer 追加一次真实 W010 构建，将原 receipt 的 dataclass/FrozenMap 全树一致篡改但保留
SourceFile bytes/hash，直接调用 W013 public builder；run/database/top 三项均在 `/header`
认证拒绝。W013 没有仅靠 W007 normalize 就接受该伪造的路径，此事不记为本任务 finding，
也不扩展上游产品合同。

## 本轮实跑、采信与限制

本轮 Python3.12.14、Linux；主 reviewer 使用现有 `/workspace/.venvs/layauto/bin/python`，
专项实际 argv/显式 env 另存 commands.json（PATH 中的 python 不补记为 venv 路径）。新探针环境
及原输出在 [证据目录](review-evidence/independent-premerge/README.md)，全部归档文件 hash
见 [manifest](review-evidence/independent-premerge/manifest.json)。未安装/更改开发依赖。

| 分工 | 证据与事实 |
| --- | --- |
| 实跑：纯数学/独立答案 | [768 项集合与 fragment 核对](review-evidence/independent-premerge/coverage/probe.stdout.json)、[无产品 import 的 oracle/raw 算术](review-evidence/independent-premerge/coverage/oracle_audit.stdout.json)；与产品算法独立，不以 matcher 自产 golden 为唯一依据 |
| 实跑：neutral/guard | [18 项拒绝及异常核对、正常控制与精确 guard](review-evidence/independent-premerge/neutral/stdout.json)；隔离 neutral 检查，不冒充捕获认证 |
| 实跑：来源/身份 | [reader→W007/W008 分层准入](review-evidence/independent-premerge/binding/stdout.json)、[actual W013 三字段攻击](review-evidence/independent-premerge/header-attack.stdout.json)，各自范围如实记录 |
| 实跑：完整公开 direct | [public 原输出](review-evidence/independent-premerge/public.stdout.jsonl)/[命令](review-evidence/independent-premerge/public.command.json)：实际 reader→W008→W009→W010→W013 build/encode/decode；成功 roundtrip、旧输入逐字节一致、canonical status 篡改拒绝、16 个原异常 object/cause/context/suppression 保真；原 retained map storage 攻击另直接调用 guard 拒绝，不冒充 captured builder 攻击。过程约192.71s，仅此次正确性探针时间，不与旧 benchmark 比较 |
| 实跑：原证据身份 | [59 项独立只读审计](review-evidence/independent-premerge/evidence/stdout.json)，审原 argv/cwd/exit/stdout/stderr/source/tool/fixture/package/environment 记录；不是重跑工程矩阵 |
| 按身份采信 | [R2 原回执](verification-r2/receipt.json) 的 Python3.10.22/3.12.14 双1731、双60源 strict typing、build、双源码外 clean 安装三路 smoke；[原 resource04](resource-attempt-04/suite.json) 按 [test-only delta](resource-r2-identity-adoption.json) 的不变工作负载采信，原6463…source_id 不改标为 R2 |
| 未覆盖 | 本轮不重复 full/typing/build/clean 安装，不重建 readback/mismatch 完整 roundtrip 或性能矩阵；这些路径按同源原证据采信。新环境没有历史安装树/解释器 binary 或固定外部 mismatch 目录，依赖/导入/hash 依据保存的不可变记录；35 个外部输入及三路93 capture hashes 核到保留 origin 字节，不冒称现场重查旧路径。真实 EDA/PDK、生产 body/U06、全套 mandatory、Stage5 生命周期/发布、完整 M1 及实际 main 合并版本均未验证 |
| 补跑触发 | 源/测试/config/依赖/输入变化、合并冲突/组合行为变化、证据缺失或身份不闭合、独立新风险/合同要求。相关产品源改变后重新冻结并完成要求的最终矩阵。仅本轮报告/证据补记或角色变化不触发双全量 |

原资源三路完整 wire 为 23,104,092 / 59,736,484 / 23,104,160B，compact 增量分别
314,874 / 315,538 / 314,878B。旧 input 的原 hex/认证仍在，没有把 input 换成不可认证 ref；
不同终端 workload 的 W013/W011、不同环境或本轮独立探针耗时均不用于宣称提速。

探针作者错误也保留：公开 runner 首稿定位错 repo，尚未启动产品即失败；coverage 首稿
误计孔洞中的 conflict 面积、oracle 脚本 Fraction 调用错误；binding 首稿误把 W007 单层
边界当成完整认证。相应原脚本/原输出及诊断保留在本轮证据目录；runner 首稿另保留修正前的复现 stderr。
修正的是探针，未改
产品/正式测试、未把这些错误计作产品 finding 或成功矩阵。

## 交回 PM

本次只新增本报告及必要有界脚本/原输出，追加任务 reviewer 区；不改 PM 要求、阶段、验收段
或 current-work。沿原 W013 分支以项目 noreply 身份提交推送并复核远端完整 SHA；最终交接
commit 以本会话交回值为准，不用其文档 HEAD 冒充新的受测产品。

PM 下一步核本报告、原证据适用性与实际待集成 head/base；在实际 main 集成版本执行与变更
相称的 direct/readback/mismatch 组合和边界验证，再决定验收与集成状态。如果发生产品/测试/
config 冲突或变更，先定向核风险并按新冻结规则验证。本 reviewer 不合 main、不删分支、
不自行验收或启动后续任务。
