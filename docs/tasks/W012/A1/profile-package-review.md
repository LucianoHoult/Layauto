# A1 已完成 profile / before 包独立核验

Reviewer `/root/a1_plan_review`；仅核对原始证据及实际包/wire内容，未重跑产品或性能样本。[脚本](profile-package-review-evidence/check.py)、[原stdout](profile-package-review-evidence/stdout.txt)/[stderr](profile-package-review-evidence/stderr.txt)及[结果](profile-package-review-evidence/result.json)保留。**498项独立轻量核验通过，未见必须项。**

## Profile 与文案

两条readback profile在18个baseline全部结束后fresh串行运行，实际完整wire再次以1MiB块与baseline before-r1实比并重算存储文件SHA，均为136,471,701B及相同hash；源码/工具/原输出身份和完整capture/result facts一致。原工程attempt在profile结束后才启动，无基准/矩阵混比。

各阶段明确具有runtime源码定位的`__init__`/`__post_init__`、认证/重建/normalize及公开encode/decode_record calls逐项相同并与summary一致；进一步仅将codec增加两行造成的后续行号位移归一后，全部可定位runtime函数calls亦相同。此口径不把stdlib/regex内部函数或`<string>`生成方法误报为逐类独立计数；完整原profile保留。

65个大hex调用的`(phase,length)`顺序逐项相同，原pattern与新pattern分别正确；窗口HWM时间序列单调且均不超过该进程最终记录峰值。旧5次刷新、新0次刷新，最大既有118,841,892字符窗口：

| 量 | before | after |
| --- | ---: | ---: |
| 窗口前RSS KiB | 347,652 | 358,520 |
| 窗口后RSS KiB | 363,556 | 358,520 |
| 窗口前HWM KiB | 3,604,172 | 501,568 |
| 窗口后HWM KiB | 7,326,636 | 501,568 |
| matcher秒（仅诊断） | 5.968508 | 0.233527 |
| 最终记录profile峰值KiB | 7,326,636 | 720,336 |

旧最大窗口刷新至旧进程最终峰值；新同输入窗口RSS/HWM不增。新峰值720,336KiB高于全部matcher窗口HWM上限648,896KiB，故在最后观测窗口后刷新；该区间仍含decode收尾、比较及profile收集，不能指定未测allocator或函数为全部原因。性能文案正确保留此残余成本并交PM决定后续，未扩大到writer/memo。

单次profile decode wall为221.043995→222.849795s，约+0.82%；已如实披露，不能替代三次无插桩decode或总耗时结论。文案已保留baseline六个小阶段观测增幅、三次有限样本和非生产上界限制，不把cumulative相加、不把窗口HWM当净分配。

## 新重建的 before 包

`before-package/`18项附件manifest和全部成功命令原输出hash闭合；102项实际`before-source.tar`字节与其源manifest及测量before一致。Git revision为`7f7c1304bdafd941791421cef64864fb1616303c`；两个实际包各100个runtime member的SHA逐项等于before/W011 runtime manifest：

- wheel SHA256：`ffff7cd43c4680024fda7efdc9f1fc912e2273b0405c9fb1645f2cb8e9212441`
- sdist SHA256：`afb9db801fd45801a8e0ec69485ee65178b707ac21fde1b2ed5d44f067b98a94`

分类明确为本次从原source重建的包，不是历史W011 blob，也不是性能样本；没有冒称本次安装/烟测before包。元数据发现失败原记录及显式no-isolation构建环境/警告保留。本段不是新A1源码的最终双安装结果，后者仍须以r2完整工程回执核验。
