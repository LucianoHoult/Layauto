from layout.logic_depth import calculate_logic_depth
from parser.netlist_parser import parse_subcircuits


def test_top_bounds_encapsulate_nested_decoder_chain():
    netlist = """
    .SUBCKT INV A Y VDD VSS
    X1 A Y INVCORE
    .ENDS

    .SUBCKT INVCORE A Y
    M1 Y A VDD VDD PMOS
    M2 Y A VSS VSS NMOS
    .ENDS

    .SUBCKT DECODER A B Y VDD VSS
    XINV0 A nA VDD VSS INV
    XINV1 B nB VDD VSS INV
    XNOR nA nB Y NOR2
    .ENDS

    .SUBCKT TOP A B OUT VDD VSS
    XDEC A B n1 VDD VSS DECODER
    XINV2 n1 OUT VDD VSS INV
    .ENDS
    """
    subckts = parse_subcircuits(netlist)
    top = subckts["TOP"]
    result = calculate_logic_depth(top, primary_input_nets={"A", "B", "VDD", "VSS"})

    assert top.bounds.xmax >= max(result.instance_depths.values())
    assert top.bounds.ymax >= max(result.y_index.values())
    payload = result.to_frontend_json(top)
    assert payload["nodes"]
    assert {"id", "type", "x", "y", "parent_module", "pins"}.issubset(payload["nodes"][0].keys())
