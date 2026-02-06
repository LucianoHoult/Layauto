from layout.logic_depth import calculate_logic_depth
from parser.netlist_parser import parse_subcircuits


def test_inverter_chain_depths():
    netlist = """
    .SUBCKT top IN VDD VSS OUT
    XINV0 IN n1 VDD VSS INV
    XINV1 n1 n2 VDD VSS INV
    XINV2 n2 OUT VDD VSS INV
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["top"]
    result = calculate_logic_depth(subckt, primary_input_nets={"IN", "VDD", "VSS"})

    assert result.instance_depths == {"XINV0": 1, "XINV1": 2, "XINV2": 3}


def test_nand_nor_depths():
    netlist = """
    .SUBCKT top A B C OUT
    XNAND A B n1 NAND2
    XNOR n1 C OUT NOR2
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["top"]
    result = calculate_logic_depth(subckt, primary_input_nets={"A", "B", "C"})

    assert result.instance_depths["XNAND"] == 1
    assert result.instance_depths["XNOR"] == 2


def test_latch_feedback_detected():
    netlist = """
    .SUBCKT top D Q
    XINV0 n1 Q INV
    XINV1 Q n1 INV
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["top"]

    try:
        calculate_logic_depth(subckt, primary_input_nets={"D"})
        assert False, "Expected feedback loop detection"
    except ValueError as exc:
        assert "Feedback loop" in str(exc)
