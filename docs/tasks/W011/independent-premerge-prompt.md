# W011 专门合并前 review 交接

```text
按 Layauto 项目规范，以未参与 W011 设计、实现或正式测试的独立 reviewer 身份，复核 W011 是否具备 main 集成条件。

恢复与版本：
- 仓库 LucianoHoult/Layauto，原分支 codex/w011-channel-identity-fin-count。先核对 checkout、远端完整 SHA 和工作区；保护既有修改，必要时建独立 worktree。
- main 起点 61775e8fde6e9ea247ec08a32067c44c3be48ff8，准备提交 81e01da1e5a6ce8e7132f3cebf8ee92bc237246f。
- 执行交付 3c464baade7b6ea8c712cfb84265490b8e3f754e；原产品修正 8917d38d916c914bfa785cb116982f3f299b38de，最终被测源码/测试/配置冻结 e89bdaa6a091f56cfaf7862dced7232d34e22514。
- 接手包含 PM 接收记录的最新原分支 head，实核上述提交及 source-manifest 的包含/等价关系。PM 后续文档补记不冒记为另一份跑过双矩阵的源码。

先读 AGENTS、协作及环境规则、W011 任务、plan/plan-review、execution/code-review、PM receipt，再按任务引用回查 architecture、实际 physical/derived/drawn/formats/rules、W007–W010 接口及 W003/W004 原要求。current-work 只用于导航，不能覆盖明确 review 范围。

检查整个 main 起点到待审 head 的交付，重点：
1. A1–A8 逐项覆盖。真实 W005 direct 和 W006 caller-read readback 经 W008–W010、同捕获 W007 组合；无额外 IO/发布，不接受跨捕获语义或 owner 拼装，attempt 不变。
2. Query 的身份定位与 exact coverage 分开；partial seed 可定位但不冒称 full annotation。每个 seed 的候选、全部 source devices/channel 的 one-to-one 与缺失/冲突可追溯。两 channel 共用 POLY 时不能把整条 gate 归给唯一器件。
3. FIN 数来自真实几何。正常完整 crossing 为 MN0=5、MP0=7；原 extraction_mismatch 为实际 4 对 source 5。完整 X 跨越、active Y 包含、边界等号、零面积/partial、同 Y 不同 X、跨 channel 长 FIN及重复/重叠均有独立依据；不默认双计数或按 bbox 去重。身份不足时几何计量可保留，source 比较必须有成立的关联。
4. source/current 比较与 target intent 分开。所有可判 NFIN/L/逐 FIN W 差异完整，零 crossing 的未测 W 明确，未知 count 不阻止可判 L/W；不宣称几何验证了 NF/M、TOY_N/P/VT 或全部 D/G/S/B 网络。W010 edges/components/T05 violation 和外部 body scope 保留；U06 与完整规则/no_change/发布仍后置。
5. Closed/immutable 公开 DTO、完整 constructor/codec 重建、别名/错型等值 scalar、来源字段/owner 参数完整认证。复核 CR-01–CR-06 的原 finding、修正及独立关闭，特别是新 semantic 嵌套 Parameter 异常、W007 expected error 后二次构造的原 cause/context/suppression。检查 normalization/codec.py、component.py 和 source_location.py 的上游改动及原 malformed 拒绝边界。
6. 独立几何/集合、捕获边界及异常验证。按实际风险选择正式回归和新探针；可按源身份采信未改变的双完整矩阵，不机械重跑双环境。区分本次实跑、历史采信、静态核对和未验证；不能只读摘要或只比较计数。
7. 实核 262 文件 source manifest/完整 snapshot、两实际包各 100 runtime、原 1465 IDs + 新 140 = 双 1605、双 typing54、双干净安装源码外 smoke、21 条命令和原输出。旧失败、两项 tests-only setup 修正及资源 gate 历史保留。原安装树不在本机时明确按归档证据采信，不能冒称重新观察或安装。
8. 单独评估资源与集成可用性。原 fresh readback 完整 Result wire 136,461,405 B，整进程 ru_maxrss 7,322,828 KiB（约6.984GiB）；长矩阵另有 9,257,804 KiB（约8.83GiB）的采样高点。RSS 非 W011 增量、采样非精确峰值、constructor 包含在 build/decode。核对来源、测量边界、有限输入和当前受限 M1 集成是否存在实际阻塞，给出证据与建议；不能把成本自动忽略，也不能凭未测最大规模虚构通过或任意新验收门。

资源执行安排：先检查本环境内存和已有进程。原环境16GiB；完整 Result codec/readback 重型命令应串行，避免与全量矩阵/其它 codec 并发。开发/修正阶段先跑新增项和受影响范围，最终冻结交付仍需双全量；本review可以采用已按身份核验的原全量/readback/安装证据，说明本次未实跑的范围。单次完整捕获/wire/重建的性能优化已单列W012（docs/tasks/W012-capture-wire-performance.md，待准备），本review核查成本与集成影响，不顺手重构；减少测试数量不能替代该优化。如资源阻塞必须路径，保留实际失败与缺口，交 PM 安排。

写入与交付：
- 只写 docs/tasks/W011/independent-premerge-review.md、必要独立复现/证据附件及 W011 任务 reviewer 区追加记录。
- 不修改产品、正式测试、固定 fixture/答案、历史报告或 PM 验收/current-work；不自行修实现、验收、合 main、删分支或启动下一任务。
- Finding 须有实际版本、复现、影响、严重性/是否必须修正、条款依据和修复交接；资源建议单列，不混入几何正确性结论。没有问题则明确剩余必须修正项0及检查限制。
- 将 review 材料提交推送原 W011 分支，沿用项目 noreply 身份，核对远端完整 SHA 后交 PM。若必须项未闭合，结论应明确暂不建议集成。
```
