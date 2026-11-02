# W004 no_change 人读报告样张

synthetic expected sample；产品未运行。INV_M1_SYNTH；5/7 FIN，NF=M=1，L=4 nm channel length，W=2 nm fin width。
baseline version 0；InitializationEvent；空 ECO 链；所有 committed changes 为0；terminal requires_review。

本地40图形、8 connector edges、6 physical components；BN/BP独立。外部6形状、2 body associations仅作绑定的只读支持，不导出、不冒充本地边。
8 net regions、2 device regions；9 raw。CUT/同标签/同格孤岛目的迁至 special/cut_islands；MARK保留。
单位为有来源的synthetic nominal 1 nm；原XY精确保留；query (y,x)/20000 micrometres。全部技术事实为toy；production_matched_body_evidence=false、LVS not_run。

| 检查身份 | 输入 | 预期证明 | 状态 | 原义务去向 |
| --- | --- | --- | --- | --- |
| geometry_readback | expected/output.gds, source.gds | exact local tagged geometry, units, top and original XY | expected_pass_not_product_run | self_consistency: local GDS semantics |
| cdl_semantics | source.cdl, target.cdl, expected/output.cdl | full ordered pins/globals/models/DGSB/parameters | expected_pass_not_product_run | self_consistency: CDL |
| json_components | expected/layout.json, oracle.json | listed components, scope and refs; incomplete snapshot disclosed | expected_pass_not_product_run | self_consistency: JSON |
| production_downstream_open_syntax | production GDS/CDL artifacts, independent downstream tool profile | independent production tool can open/parse outputs; not local semantic equality | deferred | architecture 10.5 downstream readability gate; separated from legacy readback |
| virtuoso_dry_run | frozen snapshot, ordered export edits, future SKILL, Virtuoso context | shape locate/exact match; missing/ambiguity failure and return code; no apply | deferred | records virtuoso_dry_run / architecture 10.3 and 10.5 |
| virtuoso_readback | unresolved legacy production readback inputs | retain original unresolved scope until PM closes MR-074-Q1 after revised review | deferred | old policy/report virtuoso_readback retained; neither deleted nor assumed alias |
| calibre_drc | production GDS, PDK/deck | real DRC with bound tool/deck | deferred | real_calibre_drc explicit identity mapping |
| calibre_lvs | production GDS/CDL, target, PDK/deck | matched full semantics with fresh xref | deferred | real_calibre_lvs explicit identity mapping |

其余必需检查：fixture_oracle、audit_readiness、all_mandatory_toy_rules，以及human_report/machine_report交付；本报告内pass仅是未来预期，不是本轮产品执行结果。
所有deferred：calibre_drc, calibre_lvs, production_downstream_open_syntax, virtuoso_dry_run, virtuoso_readback；coverage none，runtime/return code null，requires_review；不能汇总为pass。
MR-074-Q1仍待新版核验后由PM关闭；旧virtuoso_readback未消歧范围明确保留。
限制：无产品Stage1–6、publication、完整grid/CSP/DTO/codec/CAS、生产PDK/Calibre/Virtuoso或production downstream gate运行；无生产上传。
机器报告实际input/limitations/hash refs见report.expected.json；Manifest仅引用本包三个expected实物，size和SHA-256按实际bytes，不表示生产发布。
