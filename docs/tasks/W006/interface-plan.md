# W006 内部接口与调用次序方案

执行起点：`7320e5d6e819a422e0a446309eb039b1f05e7dd0`，干净工作区；本方案待独立接口 review。范围以 [W006](../W006-precontext-run-audit.md) 及其架构引用为准，不发布稳定 CLI。

## 请求、记录与所有权

- `domain/publication.py` 定义 versioned、runtime-validated、递归 immutable 的 `RunRequest`、typed `ContentRef`、`RunAttempt`、审计 envelope、`StageFailure`、最小 failure `RunRecord`、两类 closure、terminal reject 与 `InputsReady`。显式 canonical encode/decode 使用已有 exact codec + SHA-256；unknown fields/version/kind 与非法组合拒绝。Ref 绑定 kind/run/content digest，repository 读回校验内容和关联。
- `RunRequest` 固定 caller 的 `proposed_run_id`、`operation=create_attempt`、key、lineage、expected starting head、site 路径、raw descriptor、三组 input/raw/config-policy selections 及各组 digest；selection 是 URI + 可选 declared SHA-256。构造请求不打开文件、不解析 site。调用者跨重试保留整个请求。未知实际 hash 不回填请求；无需新 manifest 文件。
- site 路径使用显式绝对 POSIX 路径并进入 request digest，拒绝隐式 cwd。Selections 相对所选 site 目录解释；parser session 在入口解析后冻结其实际根目录，acquisition request 保存当次解析出的 path 与原 URI。绑定声明只使用这个冻结根目录及捕获时的 URI/path 映射，不在解析后重新 resolve 符号链接。未被捕获的别名不能凭后来路径碰巧相等获准。
- F1 测试独立构造 5 input + 9 raw + 13 config/policy 共 27 项，再与历史样张核对；产品不知道该计数、文件名或 examples 路径。后发现的四个可选 normalized cache 单独审计。已声明文件的实际 bytes/hash 与声明比较；成功交接前还检查每项声明确被读取。失败时只核对已读项，不给未读取项捏造 hash。
- `ToolRunResult` 只保存 fixture-reader / dummy_fixture 的实际 read/probe 成败、SourceFile bytes/hash 及执行异常，不含 Parse/findings/backlink，不声称 Calibre。Parse audit envelope 包含原 W005 ParseResult、同 run 的 ToolRun ref；内部 ParseResult.tool_run_id 单向指向该 tool identity。Evidence 与 sources 均可沿 repository refs 读回。

## 获取与解析时序

`prepare_inputs(repository, request)`：create_attempt → 获得同 run 的 process-local 编排锁 → 查询已有输入交接/terminal/失败 checkpoint → 驱动 parser 的 acquisition requests → request binding → 原子记录 immutable ToolRun、Parse、evidence 及 ready/failure 决定 → InputsReady 或失败终结。

将 W005 reader 的文件获取改为内部 coroutine：遇到 read/probe 时 yield 中立 `ReadRequest/ProbeRequest`；pipeline 调 tooling 获取，再把同一个 SourceFile（同 bytes）send 回 parser。动态依赖仍由已捕获 site/header 逐步发现，create 之前不会解析。Tooling 与 importer 互不 import。原 `read_inputs(Path, tool_run_id=...)` 保留签名和异常语义，由组件自己的文件驱动器驱动同一 parser；不创建 run。Parser session 保留已完成 evidence 的 immutable snapshot，使意外异常/中断仍可记录此前完成部分。路径解析/查重和缓存规则沿用 W005。

正常返回 `InputsReady`，含当前 unsealed attempt、ToolRun/Parse/evidence refs 及已验证输入；repository 保存交接供同请求重试读回，attempt 只有 audit revision 推进，无 canonical context、baseline、seal 或 terminal。成功读取不产生 PipelineResult。

审计发布同时保存 repository-owned `InputCheckpoint`（实际捕获、解析、binding 决定及 immutable refs）；失败 checkpoint 固定下一次 `finalize_precontext_failure` 的 key、expected revision、failure/completed refs。若审计已发布但终结在 switch 前失败，下一次入口从该 checkpoint 恢复原终结请求，不重读文件、不把最新 revision 代入另一请求。审计响应丢失先读回 checkpoint；审计未发布时返回原始内存诊断，不承诺其已可查。

## 原子域、重放与守卫

`PublicationRepository` 持有 single-writer mutex + immutable composite root（content、attempt index、idempotency entries、输入交接）；读者读同一 root。只交付 create、record_audits/输入交接、finalize_precontext_failure、load/read/snapshot 和编排串行化；无 seal/initialize/普通 close/partial 假接口。新增方法也检查 unsealed phase/revision；unsupported mode 和非空 starting head（此后端无 state publication）typed 拒绝。

每个 mutation 在同一锁内首先查 `(operation,run,key)`：同 digest 返回原 refs，不因后来 revision/phase 改变而失败；异 digest typed conflict。首次调用再查 expected revision/head、run/ref/kind/hash 和 phase。独立 staging 完成所有 sibling、pointer 与幂等 entry 后一次 root switch；create/finalize 都提供 switch 前与响应返回前故障注入点。编排锁只防同 run 重复读取；跨 run repository mutation 仍归同一个原子域。

最小 failure RunRecord 和 closure/terminal 在 finalize 同一 switch 可见，保留已完成 audits 和 typed StageFailure。RunRecord 构造本身抛 Exception 时，仅改走 `run_record_freeze_failure` closure，保留原 StageFailure、独立 freeze failure 与 completed refs；没有第二种无 RunRecord 路径，不调用普通 Stage 5 close。finalize request digest 不随第一次 freeze 成败改写，响应丢失重放返回原发布 refs。

## 异常边界与验证

预期 acquisition/config/parse/binding 错误映射 StageFailure（stage、category/code、原始原因、定位、completed refs）。pipeline 捕获意外 Exception 为 InternalStageFailure，保留 exception type/message/cause chain 与此前 completed audits；W005 facade 原样传播。KeyboardInterrupt/SystemExit 仅 best-effort 保存中断审计/失败链，随后重新抛原异常。

审计/terminal storage 失败保留已发布 root；返回显式未终结诊断结果（包含当前可见 refs 与原故障），无 pointer 时不得返回已发布 reject。switch 后异常先读回已发布相同 operation 结果，若可确认则返回该结果，否则保留“不确定/未确认发布”诊断；中断始终重抛。process-local 不承诺 crash/OOM/断电或跨进程恢复。

验证 A1–A8：真实正常/坏 site/F2 链与顺序 spy；完整请求及第二套合法路径；same-bytes/alias/schema/digest/跨记录守卫；create/finalize 重放、竞争读者原子性；freeze/storage/Exception/interrupt 注入；W005 全回归、strict typing、新增模块的 Python 3.10 与开发版验证、sdist/wheel、干净安装源码外正常/F2 smoke。实际版本/命令/未执行范围随 Git 保存。

已调查现有 W005 codec/immutable evidence、reader cache 与错误合同，以及 legacy `pipeline/run_mvp.py`。复用 W005 exact codec/parser；legacy 的先载 site、直接产生结果、隐含默认路径与输出写回不适合本接口，未迁移其实现或引入 archive runtime 依赖。Stage2–6完整组合、真实工具/PDK与 durable backend 均留后续。
