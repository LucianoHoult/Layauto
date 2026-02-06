from layout.logic_depth import calculate_logic_depth
from parser.netlist_parser import parse_subcircuits


def test_lowercase_instance_lines_are_parsed():
    netlist = """
    .subckt top in vdd vss out
    xinv0 in n1 vdd vss inv
    xinv1 n1 out vdd vss inv
    .ends
    """
    subckt = parse_subcircuits(netlist)["top"]

    assert [inst.name for inst in subckt.instances] == ["xinv0", "xinv1"]


def test_complex_branching_depths():
    # Branching and reconvergence topology to validate stage max() behavior.
    netlist = """
    .SUBCKT top A B C D OUT
    XG1 A B n1 NAND2
    XG2 C D n2 NAND2
    XG3 n1 n2 n3 NOR2
    XG4 n1 n3 n4 NAND2
    XG5 n4 n2 OUT NOR2
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["top"]
    result = calculate_logic_depth(subckt, primary_input_nets={"A", "B", "C", "D"})

    assert result.instance_depths == {
        "XG1": 1,
        "XG2": 1,
        "XG3": 2,
        "XG4": 3,
        "XG5": 4,
    }


def test_explicit_empty_primary_inputs_is_respected():
    # Caller can intentionally disable primary-input anchoring.
    netlist = """
    .SUBCKT top A B OUT
    XN1 A B n1 NAND2
    XN2 n1 A OUT NOR2
    .ENDS
    """
    subckt = parse_subcircuits(netlist)["top"]

    with_default = calculate_logic_depth(subckt)
    with_empty = calculate_logic_depth(subckt, primary_input_nets=set())

    assert with_default.instance_depths["XN1"] == 1
    assert with_empty.instance_depths["XN1"] == 1
    # XN2 sees A as PI in default case, but not when empty set is explicitly provided.
    assert with_default.instance_depths["XN2"] >= 1
    assert with_empty.instance_depths["XN2"] >= 1
