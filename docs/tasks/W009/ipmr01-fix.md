# W009 IPMR-01 执行补修

日期：2026-11-03；2026-11-04恢复续作。执行/集成：本 session `/root`。本记录不代写 reviewer 结论或 PM 验收。

## 恢复与范围

- 指定恢复提交及远端 W009：`cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`；main：`4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。初始 `/workspace/Layauto` 为 `work` 分支的 main 基线，staged/unstaged/untracked 均空。
- 实际 `git ls-remote` 与 GitHub ref 均确认上述分支身份。Git 默认沙箱无法连接继承代理，使用平台附加网络权限后查询/fetch成功；保留代理与 TLS。独立执行工作树为 `/workspace/work/w009-ipmr01`，分支为原 W009 名称。原 checkout 保留。
- 已读根 AGENTS/README、协作/环境规则、W009 原要求及 PM2、[补修交接](ipmr01-fix-task.md)、[原独立 premerge 报告](independent-premerge-review.md)、相关架构与 W008/W007 接口。恢复树只有根 AGENTS。
- 保留 IPMR-01、CR-01/CR-02、PM1/PM2及全部旧输出。只在既定合同内修复完整可达解码链，未改 wire schema、fixture/答案、几何算法、输入解释或认证义务。

## 调查与修法

`effective_codec -> geometry_codec` 重建 layout/partition/occupancy 时，原 constructor catch 按异常类把内部错误改为新 ValueError。移除该重建包裹，由 constructor 明确拒绝非法字段；`LayoutDraft._materialize` 对 preserved BOUNDARY 的完整字段集、layer policy 引用和 XY pair 长度在使用前显式校验。几何计算、重建一致性与 canonical 回编比较保留。

同时实际确认以下同链反例，并在独立执行分支窄修后由本执行者集成：

- `GeometryInput -> NormalizationInput`：两个按异常类包裹 `request_decoder_input`/`validate_parse` 的 catch 仍改写其内部错误。用实际 W005/W006 合法 result wire 注入确认；保留原始35项有效观察（34项改写、1项原样）。移除包裹，在 `_validation` 的已消费字段/来源引用上用先检查存在的 typed accessor，并补 scalar、集合、UTF-8及索引边界检查；原认证计算与比较保留。较大 diff 主要是 lookup 替换，不另建证据 schema。
- W006 readback 的 `ReadbackBinding`：semantic codec 的 constructor catch 改写 `content_ref` 内部错误。只为本轮可达的 `NormalizationInput`/`ReadbackBinding` 解除该包裹，其他 semantic DTO 历史边界保留。
- `SourceFile` 捕获重建：只替换 `evidence.py` 的 hashlib 绑定，隔离证明合法 W009 wire 的内部 hash `TypeError` 被 publication codec 改写。只为15种 W009 可达捕获/readback DTO 解除 constructor 包裹；EvidenceRecord.sources/ParseResult 的集合先检查容器形状，再单次快照、校验并保存同一快照，其他 terminal/failure codec 历史边界保留。
- 追加畸形对照发现 response count header 的空白 lexeme 可令原 `split(...)[-1]` 越界。增加非空 tokens 检查并纳入正式回归；不放宽来源、lexeme或请求关联。

具体反例和原输出在 [investigation/](ipmr01-verification/investigation/)。全局共享 hashlib patch 的10项观察明确排除；后续隔离 patch 才用于 SourceFile 边界判断。初次正式测试有2项测试构造自身的模型键大小写错误，保留失败输出并修正重跑，不记作产品 finding。962项额外字段删除/集合替换调查没有新增裸异常；其scope记录了实际加载的中间源码，未冒充最终认证通过。

独立复核另发现本轮显式集合检查引入的副作用 list 子类问题（FXR-01，P2）：先 `any(values)` 后 `tuple(values)` 会验证和保存不同迭代内容，EvidenceRecord 可保存 `(None,)`，ParseResult 可裸 AttributeError。执行者改为 shape 检查后只取一次 tuple 快照，再验证并保存同一快照；维持原 list 子类接受范围，新增4类collection×valid-first/invalid-first的8项正式回归与单次迭代断言。原 finding/独立反例和关闭由 reviewer 保存。

最终产品提交为 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9`，相对恢复提交仅8个 runtime 文件及3份新增正式测试，共新增235项（129个base、47个捕获、59个receipt用例）。wire schema及几何算法、来源/身份、原对象图校验保持；`domain.geometry`、坐标/occupancy/有效区域数学和 fixture/答案均无改动。独立 reviewer `/root/ipmr01_independent_review` 及其专项未承担这些修复或正式测试修改。

合法wire兼容另作[同捕获对照](ipmr01-verification/compatibility.json)：从恢复提交归档runtime，和最终runtime在同一解释器读取同一实际fixture及URI spelling，W008 result、W009 draft/result的全部wire字节、record digest与有效草稿semantic digest均相同。历史report的result hash受迁移checkout后的绝对normalized-cache URI影响；此对照固定同一捕获身份，避免把路径来源差异误判成wire合同变化。

## 验证与交接

最终产品/测试冻结清单含245文件、90 runtime，SHA-256 `40a60ada56e2b560d1af88fec9c16e4d60a6b1384fb042f39202edfcaefefc2c`。实际命令/解释器/cwd/HEAD/原输出及包/安装身份由 [runner](ipmr01-verification/runner.py) 与 [最终回执](ipmr01-verification/receipt.json) 保存；[证据导航](ipmr01-verification/README.md)说明每份材料的版本和含义。

8aa中间版本已实跑99/99/[]及旧最小脚本的预期旧断言失败。之后追加空白 count header guard，原材料移入 [pre-count-header-guard/](ipmr01-verification/pre-count-header-guard/)；两套中间pytest由执行者主动TERM，不作完整通过。该版 runner 另因 pip23 仅提供旧 `archive_info.hash` 字段中止3.10安装身份检查；保留原失败，修 runner 严格解析并核对旧/新两种SHA字段后，在最终产品重新冻结、构建和安装。3.12中间安装 smoke 已运行，3.10中间 smoke 未运行；均不替代最终版本证据。

5f9中间版本已完成新包/双源码外安装 smoke 和99/99/[]；独立复核随后发现上述集合副作用退步，执行者主动TERM两套未完成pytest，再归档为 [pre-snapshot-fix/](ipmr01-verification/pre-snapshot-fix/)，不作最终全量通过。本轮最终73e版本再次完整冻结、重建两包并创建两套全新安装目录，恢复过程及最终实际结果如下。


## 2026-11-04 连接恢复

原执行与review工作树、产品提交 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9`、245项最终源码与90项runtime均保留；恢复检查时远端W009仍为恢复提交，main未变。恢复后未观察到原测试进程，3.12输出停在68%后的部分用例、3.10停在58%后的部分用例，均无完整pytest/typing/总回执；不将这些片段当完整通过，也不猜测退出码。

[恢复脚本](ipmr01-verification/resume_verification.py)先重新核对同一245项源码、完整tar、两包及两个实际安装树的90项runtime，并检查已完成R3命令的HEAD、source manifest、exit0及原输出hash。仅采用已完成且同源的build/install/smoke与原99矩阵，明确未重新构建/安装。中断输出与将被替换的环境回执保存在[environment-disconnect-20261103](ipmr01-verification/environment-disconnect-20261103/)。随后从头重跑缺失的3.12完整回归、3.10受影响回归及双typing/开发环境pip check；最终连续任务回执包含`resumption`说明和实际采用/重跑范围。

恢复后先将已独立产品复核的5个修复/正式回归提交推送为原分支可恢复检查点，远端确认 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9`，main仍为 `4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。见[检查点记录](ipmr01-verification/remote-product-checkpoint.json)。此时工程回归/审计仍在续跑，不作为完整交付或PM验收；最终执行/review记录与证据稍后同分支补齐。


## 最终验证结果

| 最终实际运行 | 结果与证据 |
| --- | --- |
| 原99项完整异常矩阵 | **99/99同对象，identity_failures=[]**；[原输出](ipmr01-verification/exception-paths.stdout.txt)/[计数回执](ipmr01-verification/exception-paths.json)。九种异常/中断，完整draft/result、W009/base/捕获链 |
| Python3.12完整v2 | **1149 passed，命令耗时1071.409秒**；[stdout](ipmr01-verification/pytest-312.stdout.txt)/[回执](ipmr01-verification/pytest-312.json) |
| Python3.10受影响回归 | **988 passed，命令耗时1469.101秒**；范围是全部contracts与W006 publication unit；[stdout](ipmr01-verification/pytest-310.stdout.txt)/[scope](ipmr01-verification/pytest-scope-310.json) |
| 双strict typing与依赖 | Python3.12.14/3.10.22各**44源模块通过**，两开发环境及两干净安装的pip check均exit0 |
| 新wheel/sdist与双干净安装 | 两包和两个实际site-packages各**90个runtime文件**逐字节等于最终源码；[包身份](ipmr01-verification/package-identity.json)/[实际安装身份](ipmr01-verification/installation-identity.json) |
| 两套源码外真实组合smoke | 新3.12 wheel与3.10 sdist分别全新安装后，以`-I -B`在源码外真实读取W005/W006→W008→W009，正常/错误/codec及异常链均通过；[312](ipmr01-verification/installed-smoke-312.stdout.txt)/[310](ipmr01-verification/installed-smoke-310.stdout.txt) |

本轮新增235项正式测试覆盖base算法原异常及既有cause/context/suppression、公开DTO/嵌套wire的明确拒绝、捕获hash与semantic/readback链，以及副作用容器快照双向控制。原畸形source/unit/ref、成组value/completed伪造、输入认证、closed-value和真实组合回归包含在完整3.12及3.10受影响范围内；没有用异常类型猜测算法/输入错误来关闭问题。

**Python3.10全套v2未重跑**，其余unit parser不在本轮受改模块；相关实现、fixture及既有单元保持原字节，3.12完整覆盖，旧3.10完整914项仅按其原版本引用。几何数学算法/旧独立4418组及性能复杂度证据保留原身份；本轮未重跑无关全域穷举或性能曲线。新增字段检查有执行成本，不承诺完整认证绝对时延与历史相同。未运行EDA/PDK或改变synthetic body/U06及后续物理/发布义务。

最终source manifest `40a60ada56e2b560d1af88fec9c16e4d60a6b1384fb042f39202edfcaefefc2c`，完整快照 `09004b55b07f7a1398a797cf110c27cd6c3d703992dfffa89b1e7126b24fc8de`。新wheel `30f7c04cbb310c68e0bc1af23277fa7b971b00fecdbd9c922501b66d1a7b2926`；新sdist `5a899b664136781237d02d020a9697e7a1d57ccededc03ceee09a2ca9ce16217`。完整命令/解释器/退出码/原始stdout/stderr及包/安装URL/hash由上述机器回执保存。

独立复核见[单独报告](ipmr01-fix-review.md)及[review材料](ipmr01-verification/review/)，原IPMR-01及追加finding的关闭/保留由reviewer给出。本执行记录不自行验收；只将代码、正式回归和可访问证据提交推送原W009分支，远端完整SHA在执行交回时核对，交PM重新接收。未改current-work/PM段、未合main、未删除分支或启动W010。
