# W027 独立代码复核

复核从 `b94c03e83fe16b7037a103e1c76e24e14a5a2f56` 到 `86cafe8f06b622d22f80b4b8f35d4ec50beb7579` 的实现。执行环境为 Linux、CPython 3.12.14、单进程内存仓库。手工检查了发布输入绑定、Stage 4 全部目标及提取量、W026 正式调用、仓库编码与回读、原子关闭及旧 W006/W023 入口。本次发现的一项阻塞问题已修正，并以真实文件反例复验通过。可以交 PM 做集成验收。

## 发现与修正

在 `9f95572c7184a8f13ec9cb3b97659ad6a8f9926e`，构造含十个正确规则 ID 的正式报告。T07 行宣称 `pass`，同时持有 `PredicateExecutionError`。冻结后的单行仍可读到执行错误，整包的 `issues` 却为空，因此具备了成功关闭的条件。相同问题也适用于行状态与观测或间距证据互相矛盾的情形。

`58c47a7b79cb8be4b44a3923c46d9119b437265e` 在冻结时核对行内错误、违规证据、失败策略以及绑定目录中的声明。原始行照实保留，冲突及其位置写入 `RuleAudit.issues`，仓库据此记录失败。定向单测包括额外规则和四种内部不一致，2 项通过。[修正及回归](../../../tests/unit/test_w027_rule_audit.py)

## 独立探针

| 输入和操作 | 已核对的结果 |
| --- | --- |
| 在 C16 实际版图上另改 target.cdl 的第一个 `L=4n` 为 `L=5n`，重绑 header 并从真实发布入口运行 | Stage 4 同时留下 `UnsupportedTargetAxis`、两份 `ExtractionCountMismatch` 和目标长度的 `ExtractionValueMismatch`。两份计数证据各有 CDL 第 3 行和 `source.gds` 偏移。Stage 5 正式规则调用次数为 0。 |
| 从正常目录删除 T03 并重绑，用两个线程和屏障同时提交同一关闭请求 | Stage 4 成功。Stage 5 读回九条 `pass` 和一条 `MissingRule`，位置为 `/rules`。两线程收到同一关闭记录，正式规则调用和仓库根切换各一次。 |
| 在 C14/C15 组合真实文件上运行 W026，保留原有观测和间距对，只把两个违规行的 `status` 改为 `pass` | 仓库持有十行原 `pass` 声明，T05、T07 各有一个 `InconsistentRuleResult`。T05 的 GDS 偏移为 2096 和 1648，T07 为 2480 和 2544，哈希均与实际 `source.gds` 一致。最终状态 `sealed_no_publication`，同键重放读回原关闭记录。 |

前两项是分支集成期间的补充探针。第三项和两项定向单测绑定修正版本 `58c47a7b79cb8be4b44a3923c46d9119b437265e`。从仓库根目录复验修正，在解释器所在环境安装项目测试依赖后执行。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -q -p no:cacheprovider tests/unit/test_w027_rule_audit.py
PYTHONPATH=.:tests/contracts python -B - <<'PY'
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from docs.tasks.W027.example import stage_sample, publish_sample
from layauto_v2 import constraints, pipeline

with TemporaryDirectory() as directory:
    root = stage_sample(Path(directory), 'combined')
    repository, request = publish_sample(root, 'independent-fix')
    gds_sha = sha256((root / 'source.gds').read_bytes()).hexdigest()
    formal = constraints.check_rules

    def wrong_status(view):
        report = formal(view)
        assert {r.rule.id for r in report.checks if r.status == 'violation'} == {
            'T05.contact_enclosure', 'T07.m1_spacing'}
        return replace(report, checks=tuple(replace(r, status='pass') for r in report.checks))

    with patch.object(constraints, 'check_rules', side_effect=wrong_status) as checker:
        closure = pipeline.run_stage5(repository, request)
    assert checker.call_count == 1 and repository.replay_stage5(request) == closure
    record = repository.read(closure.run_record_ref)
    audit = repository.read(record.rule_ref)
    assert repository.read(record.failure_ref).stage == 'stage5'
    assert record.status == 'sealed_no_publication' and repository.load_head(request.lineage_id) == record.binding.head_ref
    assert len(audit.checks) == 10 and all(r['status'] == 'pass' for r in audit.checks)
    assert [i.code for i in audit.issues] == ['InconsistentRuleResult'] * 2
    for issue in audit.issues:
        offsets = [s.byte_offset for s in issue.sources if s.uri == 'source.gds' and s.sha256 == gds_sha]
        assert len(offsets) >= 2
        print(issue.message, offsets)
PY
```

## 采信范围

`e3041b1e5ec00a09cf26ad54f1095019afba1e08` 补充了独立于规则冻结的 Stage 4 分类。读取识别算子的观测，FIN 数量 `(0,)` 是实测的零，和声明冲突时返回 `ExtractionCountMismatch`。FIN 宽度的空测值 `()` 表示没有可量的条带，返回 `MissingExtractionFact`。独立分类探针确认两类原因并保留原来源。核阅了在真实 GDS 中只留下沟道外一根 FIN 的回归构造。在此版复跑规则异常与 W006/W023 原始内容地址的单测，3 项通过。[几何构造和断言](../../../tests/contracts/test_w027_planning.py) · [旧记录地址](../../../tests/unit/test_w027_wire_compatibility.py)

`86cafe8f06b622d22f80b4b8f35d4ec50beb7579` 处理首次查回执与重新打开输入之间的竞争。结合实际线程测试代码复核，并以受控的回执序列独立核对三个分支。阶段转换冲突且同一请求已有回执时返回该回执，其他键的阶段冲突原样抛出，revision 冲突保留原异常且只查一次回执。三种均不会额外调用关闭写入。

逐项审查了[Stage 4 合同](../../../tests/contracts/test_w027_planning.py)、[文件到仓库的正反例](../../../tests/contracts/test_w027_cases.py)及[重放、冲突与中断](../../../tests/contracts/test_w027_boundaries.py)的断言与生产路径。执行方的定向回归、typing 和安装证据见任务交付记录。PM 在 W027 实际合并版执行 Python 3.10/3.12 全量。后续改动若涉及规则见证、目标判定、封存引用或仓库切换，需要复验对应反例。
