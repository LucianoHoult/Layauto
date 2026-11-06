# W010 工程验证（R2）

结果：本目录记录的21条工程命令全部退出0。冻结源码提交 `0f5029df935bc0acd106aad1bc2be81304d4f442`；[完整receipt](receipt.json)与[逐文件身份](source-manifest.json)保留命令、解释器、环境覆盖、原始stdout/stderr及SHA-256。

| 验证 | Python 3.10.22 | Python 3.12.14 |
| --- | --- | --- |
| 完整v2 unit/contracts | 1465 passed，3615.88s | 1465 passed，2614.99s |
| strict mypy | 48 source files，无问题 | 48 source files，无问题 |
| 开发环境pip check | 通过 | 通过 |
| 全新安装 | 本次sdist | 本次wheel |
| 安装pip check / 源码外真实smoke | 通过 / 通过（102.576s） | 通过 / 通过（75.113s） |

两次完整测试均为原串行命令；收集结果保留原1149个nodeid并新增316个，无遗漏。上表为pytest报告时间，实际命令wall时间分别3618.420s与2616.856s；两解释器同时运行，不作生产性能保证。

`source-snapshot.tar.gz`包含252个冻结文件；94个runtime Python/py.typed文件逐字节满足源码＝新wheel＝新sdist＝两套实际安装。[包身份](package-identity.json)、[安装身份](installation-identity.json)及pip报告记录真实文件与摘要。wheel SHA-256 `f77c718aa292d8c15c37206a1543462e29888dc65e38e61cc830856f75c60232`；sdist SHA-256 `49b5fdd10ee7aca6f349dfcaea1d42292dfd647a6d05a9aa695d180d85d25d5b`。

两套安装位于checkout及冻结源码之外的全新环境，通过 `-I -B` 从源码外目录执行；实际导入均来自各自site-packages。smoke执行真实read_inputs/prepare_inputs、direct/readback W008→W009→W010链；得到14 nodes、8 edges、6 components和16条通过审计，验证W010禁IO、保留输入及attempt、公开重建和错误DTO拒绝。运行输入仅实际上游捕获fixture；snapshot内W003 records示例仅供原W006测试读取。

runner在所有命令结束后复核根目录与snapshot的源码/测试/配置文件身份和路径集合、smoke身份均未变化；归档成员及所有命令原输出摘要已另行只读核验。`evidence-manifest.json`覆盖本目录全部证据及新包（自身除外）。重放使用[runner](prepare_final.py)的参数接口，输出与work目录必须全新；环境路径只记录本次真实执行位置。

[R1失败/中断记录](../verification-r1/failure.json)与[初始preflight](../preflight/README.md)均保留。原preflight完整串行310未跑完且有snapshot缺W003 records的harness失败，不能称为原1149完整通过；R1也不作为完整矩阵通过。最终完整工程结论以本R2 receipt为准。有限合成样本、本地平坦cell和外部工具/完整生命周期的范围边界见任务及receipt；此记录不宣称PM验收。
