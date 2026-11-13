# W014 R4 最终资源选择与基线采信

本文件选择原报告，不创建或重标新suite。source为`998aa8052b3a6c89e3f87e029134ef8f6601535616c8b327d5ada44a29351a84`；W013 reference保留原`803b4c4f444f6c32f68966799d25fe8dffad31a914138633b0ed383eaa102bce`。

主样本：direct采用独占clean补测；readback/mismatch保留原R4，不重复运行。原R4 direct启动窗口与reviewer metadata after probe交叠，原件仍作正确性/身份核对，耗时不进入最终主样本。

| Case | 原始报告路径 | W013 / W014公开三阶段(s) | 耗时比 | 新增wire bytes | W014峰值MiB |
| --- | --- | ---: | ---: | ---: | ---: |
| normal-direct | `docs/tasks/W014/resources-r4-direct-clean/w014-normal-direct.json` | 54.633 / 61.894 | 1.1329 | 345944 | 196.40 |
| normal-readback | `docs/tasks/W014/resources-r4/w014-normal-readback.json` | 111.496 / 114.963 | 1.0311 | 345944 | 491.91 |
| extraction-mismatch | `docs/tasks/W014/resources-r4/w014-extraction-mismatch.json` | 56.645 / 61.919 | 1.0931 | 344703 | 204.29 |

全部106个非W014 runtime已由early保存snapshot与当前文件实际逐字节核相同；完整selected source delta只包含W014专有runtime/tests，详细列表见suite-identity-audit/adoption.json。每条命令、原stdout/stderr、report及hash/source身份都在final-selection.json中逐项引用。原资源目录和上代报告保持原样。

R3→R4原三路validwire的SHA、bytes、compact以及W010公开认证次数1/1/2均不变；clean direct与原R4 direct的这些字段也完全相同。metadata完整验证的实际成本已经包含在各公开phase中；原probe没有独立helper计时，不从单样本差异推导helper净成本或稳定性能提升。

最终主样本最高进程峰值491.91MiB；两份最高样本加2GiB reserve为2.961GiB，相对16GiB余量13.039GiB。旧W013在相同4CPU/16GiB完成双1731矩阵，仍只作调度依据；样本不保证全量上界。build和安装smoke在矩阵后串行。

本次仅轻量读证据并生成报告；未运行产品链。最终resource clearance和workers=2决定仍由root/reviewer核验。

clean direct wrapper另显式带MYPY_CACHE_DIR缓存变量（baseline未覆盖）；runtime没有该变量引用、resource argv不运行mypy。此区别单列于clean-wrapper-environment.json，Python/依赖、实际inputs和probe字节的相同性不依赖把两份command环境误写成全相同。
