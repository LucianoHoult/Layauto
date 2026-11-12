# 独立 neutral DTO 静态专项

Reviewer：`/root/independent_review/neutral_static_audit`，未参与设计或实现。
受审 runtime：`b42492fe32a70cf1819af21a9fe80f38edd43693`。只运行纯小值，
没有调用read_inputs、W010/W013 captured builder或完整矩阵，避免与三路资源测量争用。
全部新证据仅在本目录，不改产品/任务/方案或原findings。

## 内部 operator owner 一致性缺口

- [单target反例](operator_binding_probe.py)及[原输出](operator_binding_probe.stdout.json)：
  同一Draft的target.node绑定contact operators A，其唯一ContactComponent绑定B；membership
  真实引用该node的content ref，public AnnotationDraft和新codec roundtrip均接受。
- [多target反例](multiple_owners_probe.py)及[原输出](multiple_owners_probe.stdout.json)：
  一例node/component各自配对且全部contact operators相同，但target.region.operator_ref不同；
  另一例region operators相同、node/component各自配对，但同一Draft的contact operators不同。
  两例public Draft构造与codec roundtrip都接受。

反例使用合法typed refs和中立构造，既没有伪造hash preimage，也不声称synthetic refs
来自真实capture。缺口是同一个AnnotationBinding.local_ref/effective_ref下保留图内部的
operator owner矛盾。现有state/annotation.py `_validate_inputs`核membership与unit，
没有核这些保留operator refs的一致性。完整Result的外层capture认证是另一层义务，
不替代需要持久化neutral Draft的内部关系完整性。

## 可写 map backing 反例

[map_backing_probe.py](map_backing_probe.py)及[原输出](map_backing_probe.stdout.json)
用object.__new__/object.__setattr__构造**精确FrozenMap type**，将其_entries设为外部list，
传给公开MatchEvidence.policy。构造与公开encoder均接受；外部list append后原frozen DTO
的policy、content ref和wire均改变。新边界在复制/编码前只遍历items，未识别mutable storage。

这是malformed/forged对象的公开边界反例；安全FrozenMap公共constructor本身不会留该alias。
它不要求重写旧通用codec或改变旧wire，是否作为A5必须项由主reviewer结合“拒绝伪造、无可写alias、
复制前核验”的任务承诺认定。源auth缺失不是本项主张。

## 实跑与原失败

成功命令均从`/workspace/Layauto`执行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/Layauto /workspace/work/w013-env/dev312/bin/python -B docs/tasks/W013/review-evidence/neutral-static/operator_binding_probe.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/Layauto /workspace/work/w013-env/dev312/bin/python -B docs/tasks/W013/review-evidence/neutral-static/multiple_owners_probe.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/Layauto /workspace/work/w013-env/dev312/bin/python -B docs/tasks/W013/review-evidence/neutral-static/map_backing_probe.py
```

均exit0，约0.26/0.63/0.17秒，原输出分别记录错误被接受的事实。
首次单target探针命令遗漏PYTHONPATH，未加载项目包，`ModuleNotFoundError`见
[attempt-01原stderr](operator_binding_probe.attempt-01.stderr.txt)；这是review命令错误，
不是产品finding，重跑只补正确source路径。没有覆盖或删除原失败。

本专项实跑：上述轻量反例和静态源核查。采信：本任务既定方案/owner合同，不采信未跑的
产品矩阵。未覆盖：captured Result反例、资源正确性、新测试/双解释器全量/typing/构建安装。
修后必须以新源身份保留原失败并复核对应拒绝路径，不因换session重跑无关双全量。
