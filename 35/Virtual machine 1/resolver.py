import xml.etree.ElementTree as ET

ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
piezas = {
    '3647': '8T', '4019': '16T', '3648b': '24T', '3649': '40T',
    '6573': 'DiffCasing', '32270': '12T_DB', '6589': '12T_B',
    '32073': 'Eje', '3704': 'Eje', '3707': 'Eje', '44294': 'Eje', '4519': 'Eje'
}

tree = ET.parse('VirtualMachine1.dae')
print("--- EXTRACCIÓN DE ENGRANAJES ---")
for node in tree.findall('.//c:visual_scene//c:node', ns):
    geom = node.find('.//c:instance_geometry', ns)
    if geom is not None:
        u = geom.get('url').strip('#').replace('_dat', '')
        if u in piezas:
            mat = node.find('.//c:instance_material', ns)
            color = mat.get('target').strip('#').replace('-material', '') if mat is not None else 'N/A'
            m = [float(x) for x in node.find('c:matrix', ns).text.split()]
            print(f"{piezas[u]:<12} | Color: {color:<10} | Pos: {m[3]:6.1f}, {m[7]:6.1f}, {m[11]:6.1f}")
