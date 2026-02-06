from layout.ccc_analyzer import group_ccc
from layout.logic_depth import calculate_logic_depth
from parser.netlist_parser import parse_subcircuits


def test_6t_sram_bitcell_ccc_and_feedback_marking():
    netlist = """
    .SUBCKT SRAM6T BL BLB WL VDD VSS
    M1 Q QB VDD VDD PMOS
    M2 QB Q VDD VDD PMOS
    M3 Q QB VSS VSS NMOS
    M4 QB Q VSS VSS NMOS
    M5 Q WL BL VSS NMOS
    M6 QB WL BLB VSS NMOS
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["SRAM6T"]

    ccc = group_ccc(subckt)
    assert len(ccc) >= 1

    result = calculate_logic_depth(subckt, primary_input_nets={"BL", "BLB", "WL", "VDD", "VSS"})
    assert result.feedback_edges


def test_2to1_mux_tg_transparency_config():
    netlist = """
    .SUBCKT MUX2 D0 D1 SEL OUT VSS
    MTG0 OUT SEL D0 VSS TG
    MTG1 OUT SELB D1 VSS TG
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["MUX2"]

    opaque = calculate_logic_depth(subckt, primary_input_nets={"D0", "D1", "SEL", "SELB", "VSS"}, tg_transparent=False)
    trans = calculate_logic_depth(subckt, primary_input_nets={"D0", "D1", "SEL", "SELB", "VSS"}, tg_transparent=True)

    assert max(opaque.instance_depths.values()) >= max(trans.instance_depths.values())


def test_hierarchical_xdecoder_nested_subckt_depth():
    netlist = """
    .SUBCKT INV A Y VDD VSS
    M1 Y A VDD VDD PMOS
    M2 Y A VSS VSS NMOS
    .ENDS

    .SUBCKT DECODER A B VDD VSS Y0
    XINV0 A nA VDD VSS INV
    XINV1 B nB VDD VSS INV
    XNAND nA nB Y0 NAND2
    .ENDS

    .SUBCKT TOP A B OUT VDD VSS
    XDEC A B VDD VSS n0 DECODER
    XBUF n0 OUT VDD VSS INV
    .ENDS
    """
    subckts = parse_subcircuits(netlist)
    top = subckts["TOP"]

    res = calculate_logic_depth(top, primary_input_nets={"A", "B", "VDD", "VSS"})
    assert res.instance_depths["XBUF"] >= res.instance_depths["XDEC"]
