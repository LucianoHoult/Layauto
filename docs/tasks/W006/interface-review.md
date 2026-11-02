# W006 独立接口 review

Reviewer：`/root/interface_review`；未参与方案编写或产品实现。专项只读复核由 `/root/interface_review/audit_request_path` 承担请求/路径/同 bytes 边界，未写产品或方案。本报告不是 PM 验收。

## R1 身份与范围（2026-11-02）

- 仓库：`LucianoHoult/Layauto`，分支 `codex/w006-precontext-run-audit`。
- 基线/HEAD：`7320e5d6e819a422e0a446309eb039b1f05e7dd0`；启动时只有 `docs/tasks/W006/` 未跟踪文件，无已有产品修改。
- 受审材料：[interface-plan.md](interface-plan.md)，首轮 SHA-256 `af7f609778ec079156bd12f81b8f4a7a4cbd7dc27f837e2b7a782e8305e9ddc5`。
- 已读：AGENTS、README、协作规则、W006 要求；architecture §2.6–2.7、§9.2、§11.2/11.4/11.10/11.13–11.15、§12.6–12.7；W003 共享记录/F1/F2/exact-wire、W005 reader/evidence/results 及其后续组合边界。仅根 AGENTS 适用。
- 本次为静态接口/合同审查，没有运行产品测试、构建或 EDA，也没有修改 fixture/答案、实现、PM 状态或 Git 提交。

## R1 必须修正项

| ID | 原方案与反例 | 要求、影响及关闭条件 | 状态 |
| --- | --- | --- | --- |
| IR-01 | 调用顺序为“记录 immutable ToolRun、Parse、evidence → request binding → InputsReady 或失败终结”，重放只“查询已有输入交接/terminal”。若 audits 已发布而 finalize 在 root switch 前失败，attempt 已推进，但无交接或 terminal。按该顺序重试会再次读取；文件变化时可把同一 run 的事实换掉，或以相同 audit key/不同 digest 冲突而无法继续原失败终结。 | W006 §6–7/A5/A7 要求重试保持已完成事实与原请求、无半记录/伪 terminal。明确 repository 拥有的 checkpoint：保留已捕获审计、binding/失败决定及稳定的后续 operation 请求（含原 expected revision/key/digest），失败后从此继续；输入就绪与其引用必须一起发布，或提供等价可重放中间态。重试不能重新读取并覆盖原 facts。增加 audit-publication 后、terminal switch 前失败再重试且磁盘已变化的验证。 | 待执行修正、独立复核 |
| IR-02 | RunRequest 只写“site 路径”和 selections URI，未规定路径基准。相对 site 且声明 hash 未知时，相同 request/digest 随 cwd 改变可选择不同文件。若结束解析后重新 resolve 符号链接再做请求绑定，实际读入身份也可能与绑定观察不一致。 | W003 exact-wire 禁止隐式 cwd，W006 A2/A3 要求实际来源可追溯。明确绝对 site 路径，或显式 base 随请求冻结并参与 digest；selection 相对 site 目录。绑定使用捕获时记录的解析路径/URI 映射，不以事后重新 resolve 来替代实际读取身份。补路径基准/重定位与别名变化验证。 | 待执行修正、独立复核 |

两项均为既有范围内的接口细化，不需要新用户决定或额外外部 manifest。处理后可继续原授权实现；本报告不扩大产品能力或验收标准。

## 其余合同核对

- create_attempt 在所有读取/解析前，固定 caller run id，create 失败不继续；请求声明与实际 hash 分离。
- F1 的 27 项声明与四个后发现的 optional cache 分开；产品不加载样张答案，不硬编码集合。F2 采用匹配坏 header/raw 后构造的独立请求，走真实 MissingTerminator 链。
- coroutine 由 pipeline 驱动 acquisition，再将同一个 SourceFile send 给 importer；tooling/importer 互不 import，ToolRun 只有执行事实，Parse 单向关联。保持 W005 facade 的 unexpected Exception/interrupt 传播。
- mutex + 单 composite root 拥有 content、attempt 与幂等，same-key replay 先于 guards；failure RunRecord/closure/terminal 原子发布，唯一无 RunRecord 的 freeze-failure closure 不放开普通 unsealed close。
- 正常读取仅 InputsReady，仍 unsealed，无 baseline/seal/成功 terminal。未交付的 Stage2/5/6 public 方法不返回假成功。
- storage 失败区分未发布与已发布但响应丢失；interrupt 记录 best effort 后重抛；process-local 不宣称 durability、crash/OOM/断电恢复。最终代码仍须验证具体 DTO、refs、锁/事务和注入行为，方案通过不能替代 A1–A8 的实际证据。

## R2 修正复核（2026-11-02）

再次直接读取修订方案；HEAD 仍为 `7320e5d6e819a422e0a446309eb039b1f05e7dd0`。本轮受审 `interface-plan.md` SHA-256 为 `5a1b9d986871d7ca4a6f10d83e37fb65e439255807fc18e3677b2866ae712b92`。

| Finding | 独立复核依据 | 当前结论 |
| --- | --- | --- |
| IR-01 | 调用顺序已将 binding 与 ready/failure 决定放在原子审计发布前；同 root 保存 InputCheckpoint 及固定的下一次 finalize key、expected revision、failure/completed refs。重试先查 checkpoint，terminal switch 前失败只恢复原终结请求，不重读或用新 revision 改造请求；audit response-loss 先读回 checkpoint，未发布时明确只有内存诊断。 | 方案缺口关闭；对应故障窗口与磁盘变化反例须在最终实现验证。 |
| IR-02 | site 使用进入 digest 的显式绝对 POSIX 路径；selection 相对 site 目录，parser 冻结实际根目录，acquisition 保存 path/原 URI；绑定依捕获时映射，不再解析符号链接，未捕获别名不能靠事后碰巧相等获准。 | 方案缺口关闭；路径基准/重定位/别名变化须在最终实现验证。 |

**接口 review 通过，剩余必须修正项为 0。** 可按原授权进入实现，不新增用户审批。此结论只覆盖上述受审方案；不代表代码、A1–A8、W006 PM 验收或完整 M1 已通过。R1 原 finding 与反例保留，最终代码 review 应核验其实际落实。
