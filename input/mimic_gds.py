import klayout.db as pya

def create_dummy_gds(output_filename="dummy_layout.gds"):
    layout = pya.Layout()
    layout.dbu = 0.001  # 精度 1nm

    # 创建 Layer
    l_m1 = layout.layer(1, 0)
    l_po = layout.layer(13, 0)
    l_fin = layout.layer(14, 0)

    top_cell = layout.create_cell("BUFLVT")

    # 1. 插入 M1 连线 (对应 VSS 网络)
    # 坐标: [0.000, 0.000, 1.200, 0.030] -> DBU: [0, 0, 1200, 30]
    top_cell.shapes(l_m1).insert(pya.Box(0, 0, 1200, 30))

    # 2. 插入 PO (Poly) (对应 MMM1 器件的 Gate)
    # 坐标: [0.088, 0.010, 0.101, 0.305] -> DBU: [88, 10, 101, 305]
    top_cell.shapes(l_po).insert(pya.Box(88, 10, 101, 305))

    # 3. 插入两条 FIN (FinFET)
    top_cell.shapes(l_fin).insert(pya.Box(70, 100, 120, 110))
    top_cell.shapes(l_fin).insert(pya.Box(70, 200, 120, 210))

    layout.write(output_filename)
    print(f"Dummy GDS 已生成: {output_filename}")

if __name__ == "__main__":
    create_dummy_gds()
