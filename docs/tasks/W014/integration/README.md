# W014 实际 main 集成验证

被测 merge：`f8280de44beacbca6b657627cbc5eed5f2b67bdd`（[PR #70](https://github.com/LucianoHoult/Layauto/pull/70)）；受审 head：`39dba6f175fb02edab645756459403614a56b23f`。两个完整 Git tree 相同。验收结论归[任务 PM2](../../W014-terminal-body-relations.md#pm2-integration)。

- `probe.py`从实际merge checkout导入产品，核286项冻结源码/测试/config，并复用`verification/installed_smoke.py`中的计算断言，串行检查direct、readback、extraction-mismatch的公开build/encode/decode。核8端、6本地＋2独立body、T04/T05体域检查、本地图14/8/6与两未知body、原FIN差异和annotation缺口；readback保持attempt/checkpoint且无terminal。
- 正常direct另核公开digest及伪造support status拒绝。`probe.command.json`与原stdout/stderr保存命令、位置、耗时和hash；不保存新大wire副本。路径/运行身份不同，当前wire hash不能与旧固定URI benchmark作等值或提速比较。
- `boundaries.command.json`与原stdout/stderr保存正式边界回归：缺body context、缺operator、错误source绑定的reader拒绝，以及新W014和旧W007依赖guard。
- `environment-and-review.json`记录Python/依赖、14份新增review材料hash和采信边界。预合并独立工程审计838项与历史840项的差别是两处旧安装树不在该review主机；不把原包/安装证据采信冒作重建那些树。GitHub未返回CI状态，不声称CI通过。

本轮是源码树集成检查，未重新构建/安装、typing、双全量或性能矩阵；原双1889等按冻结身份采信，独立review反例保留其原执行版本。复用安装smoke的函数不等于执行其隔离安装main，本轮也未重复该main的动态禁止IO instrumentation；只读依赖guard和原同源纯度证据分别适用。

复现时从上述merge的独立checkout根目录运行`python -B docs/tasks/W014/integration/probe.py`，将原样脚本放入对应位置、输出写入新目录。脚本要求HEAD为被测merge，后续文档补记不冒记为新的受测产品；边界准确argv见命令回执。不要覆盖原证据。

仍不覆盖完整M1、通用PDK/S-D策略、全部mandatory、真实EDA/LVS、baseline/no_change/publication/Stage6。U06仅设计，当前reader仍必填body_context。
