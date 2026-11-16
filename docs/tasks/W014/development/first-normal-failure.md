# 首个实际 normal 组合失败

这是开发期真实命令失败，不计通过，也不是最终冻结产品证据。源身份保存在
[first-normal-source.json](first-normal-source.json)；身份在进程失败后、修正前采集。
对应 [完整源码快照](first-normal-source-snapshot.tar.gz) 与清单逐hash一致，tar SHA-256
为 `e88a6b1ecbcaa32115b96177eaa0a2fde1707d80da27b349ad8bfe332683a827`。
运行位置 `/workspace/Layauto`，Python 3.12.14，exec session `33613`，exit 1。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests/contracts \
/workspace/work/w014-env/dev312/bin/python -B - <<'PY'
from w014_cases import normal_capture
r = normal_capture()
d = r.value
print(r.status, [(x.code, x.source.field) for x in r.issues], flush=True)
print([(x.target.device_id.name, x.target.role, x.status, tuple(n.name for n in x.observed_net_ids)) for x in d.relations], flush=True)
print('comparison', d.comparison_status, d.source_comparison_status, flush=True)
print('body', d.body, flush=True)
PY
```

原终端输出中的失败栈末端（摘录，非独立重跑）：

```text
  File "/workspace/Layauto/layauto_v2/derive/terminal_relations.py", line 233, in __post_init__
    body, body_issues = evaluate_body(channels, annotation, self.body_evidence)
  File "/workspace/Layauto/layauto_v2/derive/body_relations.py", line 183, in evaluate_body
    active_threshold, tap_threshold = _owners(channels)
  File "/workspace/Layauto/layauto_v2/derive/body_relations.py", line 130, in _owners
    active_nm, tap_nm = rational(active['active_enclosure_nm']), rational(tap['enclosure_nm'])
  File "/workspace/Layauto/layauto_v2/domain/codec.py", line 87, in rational
    raise ValueError('expected numerator/denominator rational')
ValueError: expected numerator/denominator rational
```

原因：同源 rules schema 的阈值是 native integer 10/1；`rational` 只解码显式
numerator/denominator map。应在原 native/schema 验证后用 Fraction 精确提升整数，
不改规则阈值、输入格式或用 float 代替。该问题也由独立 reviewer 静审指出。
修正后的实际组合/定向回归另存新证据，不覆盖本记录。
