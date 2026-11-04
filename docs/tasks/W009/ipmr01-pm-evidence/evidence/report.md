# W009 补修 PM 接收：证据专项

日期：2026-11-04。只读核验者 `/root/w009_fix_pm_evidence`，由 PM 委派；未参与补修或正式测试实现，本专项不代替原独立修后 review 或 PM 最终验收。

核验对象为 `codex/w009-effective-geometry-terminals@6cb4ecc2ecaa8bd6e5236b28b70149d9a4917534`，受测产品/正式回归为 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9`，补修基准为 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`。开始时工作区干净；只在工作区外保存本专项脚本、输出和报告。

**本专项核验通过，未发现必须修正项。**

## 实际核验

- 最终 manifest 的245个源码/测试/配置文件与当前文件及产品 Git 对象逐字节一致，覆盖全部受管 runtime、unit/contracts Python 与根 README/pyproject；90项 runtime 全匹配。清单 SHA-256 为 `40a60ada56e2b560d1af88fec9c16e4d60a6b1384fb042f39202edfcaefefc2c`。
- 完整 tar 的245项、唯一普通成员及整体 hash 与清单/总回执一致；新 wheel/sdist 各90项 runtime 与源码全等，整体 hash 分别为 `30f7c04cbb310c68e0bc1af23277fa7b971b00fecdbd9c922501b66d1a7b2926`、`5a899b664136781237d02d020a9697e7a1d57ccededc03ceee09a2ca9ce16217`。
- 总回执24份命令逐项与各自 JSON 完全一致，HEAD/finished_HEAD均为产品提交、source manifest一致、exit0且全部原始stdout/stderr hash匹配。3.12全量1149项、3.10受影响988项及双44模块typing与真实输出一致；3.10范围明确是全部contracts加W006 publication unit，不含完整parser unit。
- 恢复记录的16份已完成build/install/smoke沿用、8份缺失检查重跑和14份断连归档逐项一致；命令开始时间符合恢复点边界。归档partial输出未混作完整通过；runner/smoke/resume脚本hash匹配。
- 双安装身份记录的90项 runtime、pip安装report/直接artifact URL/hash、源码外cwd和`-I -B`命令相互一致。原独立review读取的实际安装树JSON记录亦与最终runtime及来源一致；3.10可选metadata hash为空的事实保留，未伪造该字段。
- 独立review的99/99原异常矩阵、33项receipt拒绝、1184项捕获变异及FXR-01双向8项回归的回执/输出/源码身份和恢复记录匹配；集合反例修后输出没有保留None。此处是内容和版本核验，不冒称重跑这些动态检查。
- 同捕获兼容输出的恢复版/最终版各90项runtime均等于各自Git对象，源URI/fixture相同，W008 result、W009 draft/result完整wire/digest与semantic digest一致；新旧路径来源差异未被误当格式变化。
- fixture、legacy、架构、current-work、W003–W008历史材料以及W009原verification/premerge/PM1/失败材料相对补修基准均无改动。

## 实跑与采信边界

实际运行：

```sh
cd /workspace/Layauto
PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/work/w009-fix-pm/evidence/audit.py > /workspace/work/w009-fix-pm/evidence/audit-result.json 2> /workspace/work/w009-fix-pm/evidence/audit.stderr.txt
```

最终脚本 exit0、stderr为空；结果见[audit-result.json](audit-result.json)，完整可复验逻辑见[audit.py](audit.py)。脚本固定交付HEAD，PM文档提交后应从上述交付checkout复验。

两套原实际安装目录在当前主机均不存在。本次实际读取了包实物、原安装来源/字节记录和独立review实际树输出；**未重新遍历安装树、重建、重装、运行smoke、pytest或typing**。这些历史执行结论按对应版本、回执及原独立review采信；hash一致本身不是重新观察历史执行。完整产品/错误路径的动态核验由主PM及其代码专项负责。
