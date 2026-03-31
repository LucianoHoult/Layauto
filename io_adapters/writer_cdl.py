"""
CDL (SPICE) netlist writer.

Generates CDL for the modified layout after resize.
"""


def write_cdl(filepath: str, cell_name: str,
              nmos_nfin: int, pmos_nfin: int, poly_width: int = 20):
    """Write a CDL netlist file for the inverter."""
    with open(filepath, 'w') as f:
        f.write(f"* CDL netlist for {cell_name}\n")
        f.write(f".SUBCKT {cell_name} VDD VSS IN OUT\n")
        f.write(f"MN0 OUT IN VSS VSS nmos_finfet nfin={nmos_nfin} l={poly_width}n\n")
        f.write(f"MP0 OUT IN VDD VDD pmos_finfet nfin={pmos_nfin} l={poly_width}n\n")
        f.write(f".ENDS {cell_name}\n")
    print(f"  CDL written: {filepath}")
