# Layauto 项目运行流程（自顶向下）

> 本文从 **运行主文件 `pipeline/run_mvp.py` 的时间顺序** 出发，自顶向下追溯整条流水线的关键工作方式。
> 限制下探到目录 / 文件 / 函数粒度，关键变量按需提及。
> 历史背景与设计原则参见 `docs/architecture.md`。

---

## 0. 项目使命与一句话流程

**使命**：拿到一份 FinFET buffer（反相器）的现成 GDS 布局，加上"目标 CDL 网表"（仅改 `nfin` 个数），增量产出新的 GDS / CDL / JSON / 报告，并在过程中通过 CSP（约束满足）保证 DRC 正确。

**一句话流程**：
```
diff_cdl   →  pick_macro  →  resize_device (L3 macro)
   ↑            ↓              ↓ (L2 atomic ops via CSP)
 CDL 文件      driver         core/atomic_ops + csp_engine
                              ↓
                           DRCDerivator (C1 派生)
                              ↓
                        WritebackDecoder
                              ↓
                  GDS / CDL / JSON / report 输出
```

---

## 1. 入口：`pipeline/run_mvp.py`

### 1.1 启动方式
```bash
python3 pipeline/run_mvp.py [--config <site_config.yaml>] [--lvs-mode dummy|calibre]
```

- `__main__` → `_build_arg_parser` → `run_full_pipeline(site_config_path, lvs_mode)`。
- 默认 `site_config_path = tech/site_config.yaml`。

### 1.2 `run_full_pipeline` 顶层骨架（`pipeline/run_mvp.py:216`）

按时间序拆成 **7 步**（注：流水线官方编号 Stage 1 / 1.5 / 2 / 3-4 / 5 / 6 加最后的可视化 + 校验）：

| 顺序 | 阶段 | 作用 | 关键调用 |
|------|------|------|----------|
| ① | 加载配置 | 读 `site_config.yaml` + `tech` bundle | `load_site_config`, `load_tech_config_from_site` |
| ② | **Stage 1** CDL diff | 比较 original vs modified `.cdl`，得到 `nfin_targets` | `parse_cdl`, `diff_cdl`, `get_device_param` |
| ③ | **Stage 1.5** LVS 抽取 | dummy 模式拷贝 fixture / calibre 模式起子进程；解析 iXref / nXref / NET NAMES / DEVICE INFO / NET SHAPES → 中间 YAML（saved-for-later） | `extract_ixref`, `extract_net_xref`, `extract_device_info`, `extract_net_shapes` |
| ④ | **Stage 2** 解析布局 | 构造 `LayoutModel + MultiLayerGrid` | `build_layout_model` |
| ⑤ | **Stage 3-4** CSP 加载 | 建 CSP 引擎、注册 DRC、把现有 layout 注入 CSP、未标注 shape 投影成 BLOCKAGE | `LayoutSolver.setup_engine` / `load_existing_layout` / `load_b_tier_cells_into_engine` / `project_unannotated_blockages` |
| ⑥ | **Stage 5** 执行 resize | `pick_macros(nfin_targets)` → 每个 MacroCall 在事务里跑 `resize_device` | `pick_macros`, `LayoutSolver.resize_device` |
| ⑦ | **Stage 6** 输出 | 跑 C1 派生器，decoder 应用 EditOps，写 GDS / CDL / JSON / 报告，做读回校验、可视化、和 target 对比 | `DRCDerivator.derive_c1`, `WritebackDecoder.apply`, `write_gds`, `write_cdl`, `compare_gds` |

下面按时间序展开每一步。

---

## 2. ① 配置加载

### 涉及文件
- `tech/site_config.yaml` — 唯一需要按 run 修改的入口；指向 tech bundle + 输入 / 输出路径 + Calibre 设置
- `tech/config_loader.py`
  - `load_site_config(yaml)`：解析 site config，对所有路径做 `site_dir` 相对解析
  - `load_tech_config_from_site(yaml)` → 内部调 `load_tech_config(drc_yaml, layer_yaml, layermap_override)` 构造 `TechConfig`
- `tech/drc_rules.yaml` + `tech/layer_map.yaml` — DRC 规则、层映射的 YAML 数据
- `tech/layer_map.py` — 启动时读 YAML，给出 `LAYER_MAP` / `LAYER_TIER` / `tier_of(layer)` 等
- `tech/layermap_parser.py` — 可选 foundry `.layermap` 文件覆盖 `gds:` 字段

### 关键产物（变量）
- `site` dict：含 `inputs/`、`output.dir`、`calibre.*`
- `config: TechConfig`：通过属性读取 DRC 规则（`config.FIN_PITCH`、`config.OD_EXTENSION_BEYOND_FIN`、…），所有数值 100% 从 YAML 来
- `output_dir` / 各路径变量

---

## 3. ② Stage 1：CDL diff（resize 目标）

### 涉及文件
- `io_adapters/cdl_parser.py`
  - `parse_cdl(filepath) -> dict`：解析 `.SUBCKT` + `M`-prefix 行，参数支持 SPICE 单位后缀（n/u/p/m/k/meg/f）
  - `diff_cdl(orig, modified) -> List[{inst, param, old, new}]`：按实例名匹配 device，比较所有数值 param
  - `get_device_param(cdl_data, inst, param, default)`：取某实例某参数

### 时间序行为
1. 解析 `original.cdl` → `orig_cdl`
2. 解析 `modified.cdl` → `mod_cdl`
3. `diff_cdl(orig_cdl, mod_cdl)` → `resize_targets`
4. 过滤为 `nfin_targets = [t for t in resize_targets if t['param'] == 'nfin']`
5. 调 `get_device_param(orig_cdl, 'MN0'/'MP0', 'nfin', default)` 拿原始 nfin 用作后续基准
6. 若 `nfin_targets` 空 → 直接 `return`（无事可做）

### 关键变量
- `nfin_targets`：每条形如 `{'inst': 'MN0', 'param': 'nfin', 'old': 5, 'new': 4}`，是后续 `pick_macro` 的输入

---

## 4. ③ Stage 1.5：LVS 抽取（middle-file 写入，今天不消费）

> 本阶段是 M7（LVS 反馈闭合）的占位 seam：现在写出 YAML 中间文件，但 Stage 2 的 `build_layout_model` 暂不读取它们。dummy 模式默认从 `dummy/fixtures/` 拷贝。

### 涉及文件：`io_adapters/calibre_query.py`

四对 `extract_xxx` / `write_xxx_yaml` 函数，按统一的 `mode='dummy'|'calibre'` 分派：

| 抽取对象 | 抽取函数 | 解析函数 | 输出 YAML |
|----------|----------|----------|-----------|
| 实例交叉引用 (M0↔MN0) | `extract_ixref` | `parse_ixref` | `ixref.yaml` |
| 网络交叉引用 + NET NAMES（schematic→lvs→index 三段 join） | `extract_net_xref`（内部 `parse_nxref` + `parse_net_names` + `join_net_xref`） | 上述子解析器 | `net_xref.yaml` |
| 每个 layout instance 的派生 shape（按 layer 分桶） | `extract_device_info` | `parse_device_info` | `device_info.yaml` |
| 每个 net 的派生 shape | `extract_net_shapes` | `parse_net_shapes` | `net_shapes.yaml` |

### 模式分派子流程（典型例：iXref）
- `extract_ixref` → 视 `mode`：
  - `dummy`：`run_dummy_ixref` 拷贝 `dummy_source` → `ixref_path`
  - `calibre`：`run_calibre_ixref` 起子进程 `calibre -query <svdb_dir>`，stdin 流入 `INSTANCE XREF WRITE <path>` + `EXIT`
- 再 `parse_ixref(ixref_path)` 返回结构化 dict
- 主流水线再调 `write_ixref_yaml` 持久化

### 副产物变量
- `parsed_ixref`、`parsed_net_xref`、`parsed_device_info`、`parsed_net_shapes` 都返回给主流水线但今天只用于打印统计（`devices=`、`nets=`、`S/D-swaps=`、`renumbered=` 等）。

---

## 5. ④ Stage 2：构建 LayoutModel + MultiLayerGrid

### 涉及目录 / 文件
- `io_adapters/parser.py`：入口 `build_layout_model(...)`
- `core/data_model.py`：所有数据结构定义
- `core/grid.py`：`LayerGrid` / `MultiLayerGrid` / 工厂 `create_mvp_grid`

### 5.1 数据模型骨架（`core/data_model.py`）

| 类 | 角色 | 关键字段 |
|----|------|----------|
| `OccupantType` (Enum) | cell 占用类型 | `EMPTY / WIRE / VIA / DEVICE_GATE / DEVICE_DIFF / BLOCKAGE / CUT` |
| `CellState` (frozen) | CSP 域元素 | `occ_type, net_id, width_code, is_line_end` |
| `ShapeRecord` | **几何真源**（GDS rect 1:1 对应） | `layer, bbox_nm, net_id, device_id, pin_role, is_derived, provenance, suspect_tags` |
| `CellOccupancy` | B-tier 2D cell（OD/VIA0/CUT） | `layer, track_a, track_b, occ_type, owner_device_id, shared_with[]` |
| `TrackSegment` | A-tier 1D wire 段 | `layer, track_idx, start_anchor, end_anchor, net_id, bbox_nm, shape_record↗` |
| `ViaInstance` | 跨层 via | `lower_layer/upper_layer + 双 track_idx` |
| `Device` | 晶体管 | `inst_name, dev_type, nfin, pins, fin_track_indices, gate_track_idx, bbox_nm` |
| `Net` | 电连接 | `name, net_type, pins, segments, vias` |
| `LayoutModel` | 顶层容器 | `devices, nets, shape_pool, cell_name, cell_width_nm, cell_height_nm` + `annotation_coverage()` |

> **关键设计**：`shape_pool` 是几何真源；`Net.segments` 是从 net 切片建立的"working repr"；`TrackSegment.shape_record` 是回链。详见 `docs/architecture.md` §A "annotation inversion"。

### 5.2 网格系统（`core/grid.py`）

- `LayerGrid`：单层 1D 轨道（`pitch / offset / orientation('H'|'V') / min_width / legal_widths`），提供 `physical_to_track / track_to_physical / track_range`。
- `MultiLayerGrid`：
  - `layers: {name: LayerGrid}` + `ortho_pairs: {layer: ortho_layer}`（A-tier 互为正交锚）
  - `b_tier_axes: {b_layer: (axis_a, axis_b)}` + `b_tier_cells: {layer: {(a,b): CellOccupancy}}`（B-tier 2D cell 存储）
  - 关键方法：`physical_to_segment_coords` / `bbox_to_b_tier_cells` / `register_b_tier_axes` / `set_b_tier_cell` / `b_tier_cells_of`
- `create_mvp_grid(config, nmos_fin_y, pmos_fin_y, m1_tracks_y)`：注册 FIN(H) / POLY(V) / LI(V) / M1(H) 四层，pitch 全部从 `config` 拿，offset 从实际 layout 推断。

### 5.3 `build_layout_model` 时间序（`io_adapters/parser.py:388`）

1. **解析三个 JSON**：
   - `parse_calibre_device_query(device_query_path)` → `List[Device]`，每个 device 带 `_raw_fin_y`
   - `parse_calibre_net_query(net_query_path)` → `Dict[net_name, raw_dict]`
   - `parse_bbox_by_layer(bbox_path)` → `Dict[layer, [bbox dicts]]`
2. **几何先行**：`build_shape_pool(bbox_data)` → `List[ShapeRecord]`（全部 `net_id=None`）
3. **LVS 叠注**：`apply_lvs_overlay(pool, net_data, devices)` 按 `(layer, bbox)` key 在 pool 上盖 `net_id / device_id / pin_role`；多 device 同 net（如 OUT 跨 NMOS/PMOS）通过 `_device_for_shape` 的几何包含选 `device_id`。
4. **构造网格**：
   - 从 `devices._raw_fin_y` 取 `nmos_fin_y / pmos_fin_y`
   - 从 `net_data` 的 M1 shape 取 `m1_tracks_y`
   - `create_mvp_grid(config, ...)` → `grid`
5. **device 映射到网格坐标**：每个 dev 算 `fin_track_indices` 和 `gate_track_idx`
6. **构造 nets**：
   - 对每个 `(net_name, nd)`，遍历 `nd['shapes']`：
     - VIA0 → `ViaInstance`（`lower=LI`, `upper=M1`）
     - 其他在 grid 注册的层 → `TrackSegment`（带 `bbox_nm` 缓存 + `shape_record` 回链）
7. **cell 边界**：从 `layout_json` 或 `bbox_data['BOUNDARY']` 拿 `cell_width / cell_height`
8. **装配 LayoutModel**
9. **B-tier 投影**：`project_b_tier_shapes(model, grid, devices)`
   - 注册 OD/VIA0/CPO/M0_CUT/FIN_CUT 的 axes（默认 `{OD: (POLY, FIN), VIA0: (LI, M1), …}`）
   - 把每个 B-tier `ShapeRecord.bbox_nm` 投影成 `CellOccupancy` 集合，stamp `owner_device_id` + `shared_with[]`（OD diffusion sharing）

### 关键产物
- `model: LayoutModel`、`grid: MultiLayerGrid`，二者从此被 solver / decoder / derivator 共用

---

## 6. ⑤ Stage 3-4：CSP 引擎建立 + 加载现状

### 涉及文件
- `core/csp_engine.py`：`ConstraintEngine`、`GridCell`、`DRCConstraintTemplate`、`CommitDelta`
- `core/drc_constraints.py`：DRC 模板的具体子类 + `create_mvp_drc_rules()`
- `core/solver.py`：`LayoutSolver` 编排类

### 6.1 CSP 引擎（`core/csp_engine.py`）

#### 核心数据
- `cells: Dict[(layer, track, ortho), GridCell]` — 每个 `GridCell` 有 `assignment + domain + fixed`
- `constraints: List[DRCConstraintTemplate]` — 每条规则三元组 `(stencil, trigger, forbidden_states)`
- `trail: List[(pos, prev_domain, prev_assignment)]` — 事务回滚日志（M2 起捕获 assignment+domain）
- `_uf_parent / _uf_size / _uf_trail / _uf_checkpoints` — net-equivalence 并查集（M4b）
- `propagate_stats: {layer: {calls, cells_visited, time_ns}}`

#### 公共 API（按生命周期）
| 阶段 | 方法 | 说明 |
|------|------|------|
| 建图 | `add_layer(name, n_tracks, n_ortho, track_range, ortho_range)` | 申请 cells |
| 注册 | `register_drc(rule)` | DRC 模板入栈 |
| 初始域 | `initialize_domains(net_ids, layer_occ_types=)` | 每个 cell 域基于该层允许 occ 种类 |
| 事务 | `checkpoint() -> int` / `restore(cp)` / `commit_with_delta(cp)` / `commit_with_full_delta(cp) -> CommitDelta` | trail + uf 双轨 |
| 提案 | `propose_assign(pos, state) -> bool` / `propose_release(pos) -> bool` | L2 atomic ops 调它 |
| 直接 | `assign(pos, state)` / `unassign(pos)` | 内部 + 加载阶段 |
| 屏障 | `mark_blockage(pos)` / `mark_cut(pos)` | unannotated shape / cut 层 |
| 等价 | `union(a, b)` / `net_of(pos)` / `connected_to(pos)` / `connected_cells(net_id)` | M4b 并查集 |
| 调试 | `domain_stats / get_propagate_stats / print_layer / snapshot/restore_snapshot` | |

#### 传播核心（`_propagate`）
- 仅从"已确定"cell（`domain_size==1`）出发，避免假级联
- 对每条 `constraint`，若 trigger 触发，按 stencil 算邻居 → 邻居 `domain -= forbidden`
- 邻居域空 → 返回 False（DRC 违例）；邻居刚好确定 → 入队继续传播
- 全程 append `trail`，可由 `restore` 完整回滚

### 6.2 DRC 规则模板（`core/drc_constraints.py`）

| 模板类 | 规则 | 触发 → 禁止 |
|--------|------|------------|
| `SameLayerMinSpacing(layer, spacing_tracks, trigger_types)` | 同层跨 track 间距 | trigger occ_type 出现 → 邻 track（同 ortho）禁止"同 occ_type 但不同 net" |
| `SameLayerAlongTrackSpacing(layer, spacing_ortho, trigger_types)` | 同 track 沿 ortho 间距 | 类似，方向换成 ortho |
| `SameNetContinuity` | 占位 | MVP 不启用 |

`create_mvp_drc_rules()` 返回 MVP 集合：
- LI 沿 track（ortho）间距 1（VSS / VDD 共 LI track 1）
- M1 跨 track + 沿 track 间距 1
- M4e 加 OD 跨 track + 沿 track 间距 1（DEVICE_DIFF 触发）
- M4e 加 VIA0 跨 track 间距 1（VIA 触发）

### 6.3 Solver 编排（`core/solver.py:LayoutSolver`）

- `__init__(model, grid, config)` 暂不建引擎
- `setup_engine(layers_to_include=['LI','M1'], b_tier_layers=None)`：
  1. 对每个 A-tier layer，按现有 segments 的 track / ortho 范围 + margin 调 `engine.add_layer`
  2. 自动发现 B-tier layer（OD / VIA0 等已被 parser stamp 过的），按 `b_tier_cells` 范围加入；按 layer 给 `layer_occ_types`（OD→DEVICE_DIFF、VIA0→VIA、cut→CUT）
  3. `register_drc` 全部 MVP 规则
  4. `engine.initialize_domains(net_ids, layer_occ_types)`
- `load_existing_layout()`：遍历 `model.nets`，为每段 segment 的 span 上的 cell 调 `engine.assign(pos, CellState(WIRE, net))`；via 同理两端各 stamp 一次。某次 assign 失败 → return False（说明输入本身违规，几乎不可能）。
- `load_b_tier_cells_into_engine()`：把 `grid.b_tier_cells` 里的 OD/VIA0 cell 透传到 engine（同样 `engine.assign`）。
- `project_unannotated_blockages()`：遍历 `model.shape_pool`，未标注 + 在 CSP 层上的 shape 投影成 BLOCKAGE（`engine.mark_blockage`）。冲突保守跳过并计 `skipped_conflict`。

---

## 7. ⑥ Stage 5：执行 resize（L4 → L3 → L2 → L1）

### 涉及文件
- `core/macros/pick_macro.py`：L4 dispatch
- `core/solver.py:resize_device`：L3 macro（`device_resize`）
- `core/atomic_ops.py`：L2 atomic primitives
- `core/csp_engine.py`：L2 透过 propose_assign / propose_release 改动 cells
- `core/diff.py:EditOp`：L1 记录类型

### 7.1 L4 dispatch（`core/macros/pick_macro.py`）

- `pick_macro(diff_entry, model)`：今天表里只有 `param == 'nfin' → MacroCall('resize_device', (inst, new), diff=...)`；其他参数返回 `None`。
- `pick_macros(diffs, model)` 是 batch 包装。
- `MacroCall.execute(solver)`：用 `getattr(solver, macro_name)` 找方法并调用 → 进入 L3。
- 主流水线循环：
  ```python
  macro_calls = pick_macros(nfin_targets, model=model)
  for call in macro_calls:
      r = call.execute(solver)
      results[call.diff['inst']] = r
      if not r.success:  return  # 任何失败立即终止
  ```

### 7.2 L3 macro：`LayoutSolver.resize_device(device_name, new_nfin)`（`core/solver.py:352`）

整个体在一对 `engine.checkpoint()` / `engine.commit_with_full_delta(cp)` 包裹的事务里跑；任一 `propose_*` 失败即 `engine.restore(cp)`。

#### 步骤
1. 校验 `device.nfin > new_nfin`（仅支持收缩）。
2. **顶部移除策略**：从 `device.fin_track_indices` 取 `removed_fin_tracks = old[-Δ:]`；保留 `remaining = old[:-Δ]`。
3. 计算 `old_top_fin_y / new_top_fin_y / old_bot_fin_y / new_bot_fin_y`。
4. `cp = engine.checkpoint()` 开事务。
5. **5 个子动作（按层）**——见 7.3。
6. `engine.commit_with_full_delta(cp)` 拿到 `(cells_delta, unions_delta)` 并打印计数。
7. 返回 `ResizeResult(success, message, edit_ops, new_segments, ...)`。

#### 7.3 子动作 → L2 atomic 映射（`core/solver.py + core/atomic_ops.py`）

| 子动作 | 助手 | 调用的 L2 atomic | 产出的 L1 EditOp |
|--------|------|------------------|------------------|
| (1) FIN 移除 | `_emit_fin_removes` | `atomic_ops.remove_fin_strip` 改 `model.shape_pool` | `remove_shape FIN` |
| (2) OD 缩短 | `_emit_od_modify` | `atomic_ops.extend_od` 改 grid b_tier_cells + `shape_record.bbox_nm` | `modify_shape OD` |
| (3) LI S/D bar 缩短 | `_reshape_li_sd_bars` | 关键的 L2 + CSP 路径：`atomic_ops.modify_segment(engine, …)` 在 LI 层 propose_release / propose_assign（via 覆盖必要时延伸） | `modify_shape LI`（最终 bbox） |
| (4) POLY 端点偏移 | `_emit_poly_modify_if_endpoint_changed` | `atomic_ops.extend_poly` 给出 `(target='y1'|'y2', old, new)` 三元组 | `modify_shape POLY`（**partial bbox**，`(None, y1, None, None)` 模式） |
| (5) commit | inline | `engine.commit_with_full_delta(cp)` | — |

#### 关键 L2 atomic 函数（`core/atomic_ops.py`）

- `release_segment_cells / assign_segment_cells / modify_segment` — A-tier wire 重塑，全经 `propose_*`
- `add_cut_cell / remove_cut_cell` — CPO/M0_CUT/FIN_CUT，调 `engine.mark_cut` + grid 同步
- `mark_shared_diffusion` — 跨 device OD cell 的 `shared_with` stamp + 邻接 OD cell 上 `engine.union`
- `extend_od` — OD bbox 改时，重投 cell 集合 + 按 device 包含选 owner
- `add_fin_strip / remove_fin_strip` — 直接增删 `model.shape_pool` 中的 FIN ShapeRecord
- `extend_poly` — partial-bbox endpoint 助手（不动 shape_pool，让 decoder 来匹配）

#### LI 重塑细节（`_reshape_li_sd_bars`）

- 取 device 所属 S/D nets，遍历每条 net 的 LI segments
- **device 归属判断**（M4c）：优先 `seg.shape_record.device_id`；旧路径降级到 `device.dev_type in seg.desc`
- 计算 `new_y_max = max(new_top_fin_y + 5, max(via_y_positions) + enc_y)`：保证 via 覆盖
- 调 `atomic_ops.modify_segment(engine, 'LI', track_idx, old_range, new_range, net_name)`
- 任一 propose 失败 → 返回错误字符串 → caller `engine.restore(cp)`

### 7.4 L1 记录（`core/diff.py:EditOp`）

```
EditOp(op_type, layer, old_bbox, new_bbox, net_id, desc)
```
- 4 种 `op_type`：`remove_shape / add_shape / modify_shape / resize_device`
- 由 L3 macro 直接构造（**非 CSP 派生**）；macro 把 final bbox 嵌进去，decoder 不再做几何派生

---

## 8. ⑦ Stage 6：输出（C1 派生 + decoder + writers）

### 8.1 C1 派生（`core/drc_derivator.py:DRCDerivator`）

- 主流水线在 macro commit 之后调：
  ```python
  derivator = DRCDerivator(model, grid, config)
  edit_ops_c1 = derivator.derive_c1(nmos_fin_y_new, pmos_fin_y_new)
  ```
- `derive_c1` 走两条派生：
  - `_derive_nwell` — `y2 = pmos_fin_y[-1] + config.NWELL_MARGIN_BEYOND_FIN`
  - `_derive_boundary` — `y2 = pmos_fin_y[-1] + config.BOUNDARY_MARGIN_BEYOND_FIN`
- 每个动了 bbox 的 `ShapeRecord` 被 `_mark_derived` 盖 `is_derived=True` + `provenance='drc_derivator._derive_xxx'`，并产出 `modify_shape` EditOp（**partial bbox**，仅 `y2` 维有值）。
- 主流水线把 `edit_ops_n + edit_ops_p + edit_ops_c1` 一起喂 decoder。

### 8.2 Writeback decoder（`core/decoder.py:WritebackDecoder`）

入口 `apply(orig_data, edit_ops, new_nmos_nfin, new_pmos_nfin, model)`：

#### 守门：M6 `_reject_derived_edits`
- 检查每条 EditOp：若其 `(layer, old_bbox)` 命中 `model.shape_pool` 中 `is_derived=True` 的 record，**且** 该 op 不是派生器自己发的（`desc` 不以 `derived_` 开头），抛 `DerivedShapeEditError`。

#### Phase 1 — 应用显式 EditOps（每层一个 helper）
- `_apply_fin_removes` — 按 center-Y 匹配 + 删除（避开 FIN_WIDTH 奇偶问题）
- `_apply_od_modifies` — 按 exact `old_bbox` 匹配 + 替换
- `_apply_li_modifies` — exact 匹配；macro 已嵌 final bbox，decoder 仅替换
- `_apply_poly_modifies` — **partial bbox** 模式：`old_bbox = (None, y1, None, None)`，匹配 `s['y1']==old_y1` 然后替换该坐标
- `_apply_nwell_modifies` / `_apply_boundary_modifies` — 派生器产物，partial-bbox 同模式

#### Phase 2 — 元数据更新（`_update_metadata`）
- 写 `params['nmos_nfin']/['pmos_nfin']/['nmos_fin_y']/['pmos_fin_y']/['cell_height']`
- 同步 `result['devices']` 列表

返回 `resized_data` dict，主流水线据此写 GDS / JSON / CDL / 报告。

### 8.3 Writers

- **GDS**：`io_adapters/gds_io.py:write_gds(layout_data, filename, layer_map)`
  - 优先 `_write_gds_gdstk`（gdstk 库），降级 `_write_gds_manual`（stdlib `struct`，`dummy/gds_writer.py`）
  - 同模块还有 `read_gds / compare_gds / gds_to_bbox_by_layer` 用于读回校验
- **CDL**：`io_adapters/writer_cdl.py:write_cdl(filepath, cell_name, nmos_nfin, pmos_nfin, poly_width)` 直接 `print` `.SUBCKT/MN0/MP0/.ENDS` 四行
- **JSON**：直接 `json.dump(resized_data)`
- **annotation_coverage 报告**：`model.annotation_coverage()` → `output/annotation_coverage.txt`
- **resize_report.txt**：遍历 `results[inst].edit_ops` 打印每条 EditOp
- **SKILL 脚本（备用）**：`io_adapters/writer_skill_script.py:generate_skill_script` 把 EditOps 翻译成 SKILL（M7 production seam，本流水线未默认调用）

### 8.4 GDS 读回校验
- `gds_to_bbox_by_layer(resized_gds, layer_map=config.LAYER_MAP)` 读回，与 `resized_data['shapes']` 逐 `(x1,y1,x2,y2)` 对比
- 任何 mismatch 在终端 STDOUT 报告，不阻断流程

### 8.5 可视化（`pipeline/run_mvp.py` 内联）
- `generate_three_way_comparison(orig, resized, target)` → `output/resize_comparison.png`
- `generate_diff_overlay(orig, resized)` → `output/resize_diff.png`（gray=unchanged, red=removed, green=added）

> 模块化的视图代码 `visualization/` 目录（`layout_viewer.py / diff_viewer.py / grid_viewer.py / csp_debugger.py / gds_overlay.py`）是更全面的版本，主流水线没用到（保留供调试）。

### 8.6 与 target 对比
- 优先 `compare_gds(resized.gds, target.gds, layers=[FIN, OD, POLY, LI, VIA0, M1])` 计每层 diff
- gdstk 不可用时降级到 JSON-level 比 set
- 终端汇总 `RESULT: PERFECT MATCH` 或 `N shape mismatches`

---

## 9. 三套真源 + 四层架构（理解全局的两条主轴）

> 这是 `docs/architecture.md` 总结的两条核心原则，也是本流水线的不变量。

### 9.1 三套真源（`§A`）
| 真源 | 角色 | 实体 |
|------|------|------|
| GDS | **几何**真源 | `LayoutModel.shape_pool` 中每个 `ShapeRecord` |
| CDL | **语义**真源 | `LayoutModel.devices` + `LayoutModel.nets` |
| LVS | **覆盖不全**的注解 overlay | `apply_lvs_overlay` 给 ShapeRecord 盖 `net_id/device_id/pin_role` |

未被 LVS 覆盖的 shape → `project_unannotated_blockages` 投成 BLOCKAGE。

### 9.2 层 Tier dispatch（`§B`，`tech/layer_map.yaml` 配置）
| Tier | 层 | 数据结构 | 进 CSP？ |
|------|-----|----------|----------|
| **A** 1D track | FIN, POLY, LI, M1 | `TrackSegment` | 是 |
| **B** 2D cell | OD, VIA0, CPO, M0_CUT, FIN_CUT | `CellOccupancy` | 是 |
| **C1** 派生 | NWELL, VT, PP, NP, BOUNDARY, DNW | 无 grid，由 `DRCDerivator` 派生 | 否 |
| **C2** 注解 | DIODE, ESD, TEXT | 直接 ShapeRecord 编辑 | 否 |

### 9.3 四层 Edit 架构（`§C`）
```
L4 Pipeline   :  diff_cdl → pick_macro → execute → writeback
                 (pipeline/run_mvp.py + core/macros/pick_macro.py)
L3 Macro      :  device_resize / share_diffusion / split_diffusion / add_cut / remove_cut
                 (core/solver.py:resize_device + core/macros/*)
L2 Atomic op  :  modify_segment / extend_od / extend_poly / add/remove_fin_strip /
                 mark_shared_diffusion / add/remove_cut_cell  (core/atomic_ops.py)
                 ↳ 全部经过 engine.propose_assign/release，不直接产 L1
L1 Shape rec  :  EditOp(remove_shape | add_shape | modify_shape | resize_device)
                 (core/diff.py)
```

**职责严格分离**：L2 只产 CSP 提案；CSP 引擎裁可行性 + 维护并查集；decoder 是 L1 的唯一消费者；C1 由派生器单独产 L1。

---

## 10. 入口 / 出口 / 旁路 速查表

| 类型 | 路径 | 注 |
|------|------|----|
| 主入口 | `pipeline/run_mvp.py` | `__main__` → `run_full_pipeline` |
| 备用入口 | `core/solver.py:run_mvp_resize` | 跳过 CDL diff，硬编码 MN0 4 + MP0 6 |
| 配置入口 | `tech/site_config.yaml` | run-time 唯一应改的文件 |
| dummy 数据生成 | `dummy/gen_buffer_layout.py:generate_all_fixtures` | 重建 `dummy/fixtures/*` |
| 输出目录 | `output/` | `buffer_resized.{gds,json,cdl}` + `resize_{report,comparison,diff}.{txt,png}` + `annotation_coverage.txt` + 4 个 LVS 中间 yaml + `iXref.temp/nXref.temp/net_names.txt/device_info_*.txt/net_shapes_*.txt` |
| 校验 | `pipeline/verify.py` (`verify_json/verify_gds/verify_drc`) | 主流水线内联了简化版 |
| 测试 | `tests/unit/test_*.py` + `tests/integration/test_*.py` | 覆盖每个 stage |
| 可视化（独立） | `visualization/*.py` | 主流水线未使用，保留调试 |
| SKILL 输出（M7 seam） | `io_adapters/writer_skill_script.py` + `scripts/virtuoso_apply_edit.il` | 主流水线未默认调用 |

---

## 11. 一份典型运行的"事件序列"（伪代码精简版）

```python
site = load_site_config('tech/site_config.yaml')
config = load_tech_config_from_site(site_config_path)            # ① 配置

orig = parse_cdl(original_cdl);  mod = parse_cdl(modified_cdl)   # ② Stage 1
nfin_targets = [t for t in diff_cdl(orig, mod) if t['param']=='nfin']

extract_ixref(...);  extract_net_xref(...);                       # ③ Stage 1.5
extract_device_info(...);  extract_net_shapes(...)               # 写 4 个 yaml

model, grid = build_layout_model(...)                            # ④ Stage 2
solver = LayoutSolver(model, grid, config)                       # ⑤ Stage 3-4
solver.setup_engine(['LI','M1'])
solver.load_existing_layout()
solver.load_b_tier_cells_into_engine()
solver.project_unannotated_blockages()

results = {}                                                     # ⑥ Stage 5
for call in pick_macros(nfin_targets, model=model):
    cp = engine.checkpoint()
    r = call.execute(solver)            # → resize_device
    if not r.success:  engine.restore(cp);  return
    results[call.diff['inst']] = r

edit_ops_c1 = DRCDerivator(model, grid, config).derive_c1(...)   # ⑦ Stage 6
resized = WritebackDecoder(grid, config).apply(
    orig_data, edit_ops_n+edit_ops_p+edit_ops_c1,
    new_nmos_nfin, new_pmos_nfin, model=model)

write_gds(resized, 'buffer_resized.gds', layer_map=config.LAYER_MAP)
json.dump(resized, open('buffer_resized.json','w'))
write_cdl('buffer_resized.cdl', cell_name, new_nmos_nfin, new_pmos_nfin)
# annotation_coverage / resize_report / GDS 读回 / 可视化 / target diff
```

至此，从 `python3 pipeline/run_mvp.py` 到 `output/` 的全部产出，每一步都落到具体目录 / 文件 / 函数。

---
*文档由从 `pipeline/run_mvp.py` 顶向下追溯生成；引用所有提及的源码均来自当前分支 `claude/document-project-flow-YV6H8`。*
