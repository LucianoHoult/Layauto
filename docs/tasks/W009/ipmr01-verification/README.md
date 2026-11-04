# W009 IPMR-01 新证据

本目录只存本轮补修材料。旧 `verification/`、`independent-premerge-review/`、`ipmr01-pm-confirmation/` 保留原版本含义，不改写。

- `start-state.json`：原 checkout、恢复/远端身份与运行环境；其中工作树状态是首次编辑后的观察，初始干净事实单独记录。
- `source-manifest.json`、`source-snapshot.tar.gz`、`source-snapshot-audit.json`：最终受测的全部 runtime、tests 和根 build 配置/README；含新增正式测试。清单绑定产品提交；执行/review文字与证据不追求包含自身最终hash。
- `resume_verification.py`、`resumption.json`及`environment-disconnect-20261103/`：11月4日恢复同一工作区，保留中断输出，重新核对原已完成构建/安装/99项证据，完整重跑缺失的pytest/typing；不把部分输出当完整通过，也不冒称重建或重装。
- `runner.py`：复验入口。`receipt.json` 记录真实执行结果；各命令的 `.json` 与 `.stdout.txt`/`.stderr.txt` 保存命令、解释器、cwd、HEAD、清单、退出码、耗时及输出hash。
- `pytest-scope-310.json`/`pytest-scope-312.json`：两解释器实际范围。3.12完整 v2；3.10覆盖所有 contracts 及 W006 publication unit，未冒称重跑全部 unit parser。双 strict typing 覆盖项目配置的44源模块。
- `check_paths.py`、`exception-paths.*`：直接执行原 `exception_paths.py`，除了进程exit0还检查 `case_count=99`、`same_object_count=99`、`identity_failures=[]`。
- `historical-minimal.*`：直接执行原主 reviewer 最小脚本。脚本断言旧缺陷存在，修后应在旧 `observation` 断言退出1；此退出码不作产品失败。新正式测试和99矩阵断言修后合同。
- `compatibility.json`、`normal_wire_compatibility.py`及两份原输出：恢复提交runtime与最终runtime读取同一实际捕获/URI spelling，W008 result、W009 draft/result的wire字节与digest逐一相同。迁移checkout会改变W005已记录的绝对cache URI，不拿异路径历史result hash直接比较。
- `package-identity.json`、`dist/`：本次新 wheel/sdist，分别核对全部90项runtime与清单逐字节相同。
- `clean-environment-preflight.json`、`install-*-report.json`、`installation-identity.json`：两套原先不存在的虚拟环境；3.12来自新wheel、3.10来自新sdist。保存artifact URL/hash与实际site-packages文件身份。
- `installed_smoke.py`/`installed-smoke-*`：源码树外真实 `-I -B` W005/W006→W008→W009正常、错误、codec，以及嵌套异常和既有cause/context保真见证。成功只说明当前synthetic组件子集。
- `pre-count-header-guard/`、`pre-snapshot-fix/`：两次最终冻结前的中间源码/包/输出；完整回归因继续修复主动中止，不能冒充最终通过。
- `investigation/`：执行侧确认追加同类边界的原始反例、专项输出及其版本。标明无效hash patch观察和测试编写失败，不将其混为最终通过。
- `environment-setup/`：本轮解释器、依赖安装的实际命令、原输出及身份。
- `review/`：未参与修复者独立复核材料，结论由 reviewer 维护；执行者不代写。

最终结论以实际回执和独立报告为准。Python3.10全套unit未重跑；几何数学算法及其历史复杂度/有限规模证据按原产品身份和保护路径零差异引用；本轮增加字段取用检查和集合快照校验，未重测规模曲线，不将完整认证耗时等同历史或承诺生产性能。未运行EDA或进行PM验收/main集成。
