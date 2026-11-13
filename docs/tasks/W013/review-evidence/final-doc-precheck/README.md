# 最终文档与固定输入独立预核

Reviewer：`/root/independent_review/neutral_static_audit`，2026-11-12。
本轮仅只读核对文档、Git对象、输入文件与已保存回执；没有import产品或执行
capture/performance/pytest/typing/build/install/smoke，没有改源码/测试/config/冻结工具。
只写本新目录，不改其他reviewer报告、任务或旧证据。

受审文档及精确SHA见 [precheck.stdout.json](precheck.stdout.json)。基线HEAD
`2a45938aba8e751183d472d660a1ab66a1063636`，R2完整source_id
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。

## 核对结果

[独立预核脚本](precheck.py)实跑22项只读检查全部通过，0失败；
[原stderr](precheck.stderr.txt)为空。命令从仓库根目录执行：

```sh
/workspace/work/w013-env/dev312/bin/python -B docs/tasks/W013/review-evidence/final-doc-precheck/precheck.py
```

- 官方固定输入审计的137项，实际由3项全局身份/路径/fixture检查、35个固定文件检查、
  每路2个集合/URI检查，以及三路合计93个capture-source检查组成；全部真实为True，0失败。
- 原外部URI恰35文件，逐路径/字节/SHA对应原A1 preflight及origin、恢复回执和R2映射。
  原A1 preflight与准备基线Git对象相同；旧A1目录对准备基线无diff。
- 三路各31个唯一capture URI及其实际文件、原resource04 JSON SHA、记录字节/hash逐项闭合。
  normal direct/readback仍用原fixture根，mismatch仍用固定外部根；各路径均处于相应根内。
  不使用安装smoke的临时mismatch路径作性能对照。
- 全116个fixture在A1、R2完整映射、当前工作区及R2真实执行snapshot一致。
  当前273项完整source/test/config/输入映射与snapshot均等于R2冻结身份。
- resource04仍保留测量source_id `6463eb67…3443a9`，未改标为R2 `2c5724a9…eec278`。
  本预核核输入身份，不替代已有只读test delta采信review或最终工程审查。
- 任务PM要求/阶段及PM验收段保持准备基线原字节，旧codec、架构、current-work、roadmap、
  collaboration和fixture保护路径无diff。原失败矩阵的controlled-stop、failure和双日志均保留，
  没有把首轮停止结果当成全量通过。

手工审查的范围结论：`handoff-scope-audit.md`、`final-evidence-review.md`及任务执行段
明确区分原调查、首轮失败、新R2冻结与各阶段pending；未把安装smoke待执行或review必须项0
冒作A8完成。P01按用户选A保留007拒绝，未声称扩展捕获；14/8/6本地范围、外部body独立、
component关联不代表直接query覆盖以及无baseline/terminal/完整M1/真实EDA的限制一致。

预核时R2 `receipt.json`/`failure.json`尚未出现，两套安装smoke完成command receipt均未出现。
这是当时文件状态，**不是最终smoke失败或通过结论**。即使后续所有命令完成，仍应由最终
工程review核新的完成回执；本报告不提前签完整产品或PM验收。

## 早期中立专项README引用的追加补正

发现我早期 `neutral-static/README.md` 在原manifest落盘后追加了target分类节，导致当前
README字节不再等于原manifest所记的初版hash。原probe/输出/原失败字节全部未变；
原manifest也未被改写。这是历史README定位缺口，不涉及产品源身份或矩阵。

本目录保存按追加节前缀恢复的[初版README字节](neutral-static-README.initial.md)，
SHA-256 `296c985b003b8f6429729086785eb940c841e3e981fd22a368c5dd2eeed44e7e`，
与原manifest原记录完全一致；[不可变引用补正](neutral-readme-reference-correction.json)
同时记录原manifest SHA、初版路径/hash、现追加README hash，以及原manifest全部旧批probe/
输出逐项的原hash与当前hash，全部相同。

原manifest只覆盖它原先列出的旧批probe/输出及初版README，**不追认后来追加的target分类
附件由原manifest覆盖**。后续分类probe继续由其独立identity.json/patch绑定。
本轮没有修改旧manifest/README/原probe/原输出或任何冻结源；主reviewer可据此闭合历史引用。

## 验证分工

本轮实跑仅22项只读身份/路径核查和文档语义审阅。按身份采信原137项输入审计、原失败、
既有资源及产品review的原owner记录；不重造同一capture或安装树。未覆盖最终工程receipt
完成核验、全部代码review和PM验收。源/测试/config/输入/依赖改变、原证据缺失/身份不闭合
或新风险触发对应复核；仅本目录文档/证据补正不触发双全量。

## Historical byte snapshot link base

`neutral-static-README.initial.md` preserves the original README bytes. Its relative
links resolve from the original [neutral-static directory](../neutral-static/),
not from this snapshot directory. The appended [original README](../neutral-static/README.md)
and its separate historical hash correction remain available. No raw snapshot or
probe is rewritten or copied to make those historical links resolve here.

This link-base note was added after this directory's first manifest. That manifest
keeps its original bytes; its README entry refers to the preserved
[README before this note](README.before-link-base.md). The
[link-base and version addendum](readme-link-base-addendum.json) records both README
versions and resolves the seven historical hrefs against their original base.
[The additional manifest](manifest-link-base.json) binds this later documentation
state without rewriting the earlier manifest or claiming extra product checks.
