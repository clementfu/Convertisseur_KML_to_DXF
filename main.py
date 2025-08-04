#Version qui marche, qui affiche un calque par placemark. Les cotations sont des calques mais n'apparaissent pas dans le fichier DXF. 
import os
import re
import xml.etree.ElementTree as ET
from pyproj import Transformer

# Charger le fichier KML
kml_file_path = "/kaggle/input/test-limoges/LIMOGESBELLEGARDE-LFBL-03-21principale.kml"
tree = ET.parse(kml_file_path)
root = tree.getroot()
namespace = {"kml": "http://www.opengis.net/kml/2.2"}

# Nettoyage des noms de calque
def clean_layer_name(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

# Récupérer les placemarks avec les 2 derniers niveaux de dossier
def extract_placemarks_with_path(folder_elem, path):
    placemark_data = []
    
    name_elem = folder_elem.find("kml:name", namespace)
    folder_name = name_elem.text.strip() if name_elem is not None else "SansNom"
    new_path = path + [folder_name]

    for placemark in folder_elem.findall("kml:Placemark", namespace):
        placemark_name_elem = placemark.find("kml:name", namespace)
        placemark_name = placemark_name_elem.text.strip() if placemark_name_elem is not None else "Unknown"
        coordinates_elem = placemark.find(".//kml:coordinates", namespace)
        if coordinates_elem is not None:
            coordinates = coordinates_elem.text.strip()
            short_path = new_path[-2:]  # Garde les 2 derniers dossiers parents
            layer_name = "_".join(short_path + [placemark_name])
            placemark_data.append((layer_name, coordinates))

    for subfolder in folder_elem.findall("kml:Folder", namespace):
        placemark_data += extract_placemarks_with_path(subfolder, new_path)

    return placemark_data

# Récupération de tous les placemarks
placemark_data = []
for top_folder in root.findall(".//kml:Document/kml:Folder", namespace):
    placemark_data += extract_placemarks_with_path(top_folder, [])

# Transformations
transformers = {
    "WGS84": lambda lon, lat: (lon, lat),
    "Lambert93": Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True).transform
}

# Générer les DXF
dxf_outputs = {}
for proj_name, transform in transformers.items():
    dxf = """0
SECTION
2
HEADER
0
ENDSEC
0
SECTION
2
TABLES
0
TABLE
2
VPORT
5
21
330
8
100
AcDbSymbolTableRecord
100
AcDbViewportTableRecord
2
*Active
70
0
10
0.0
20
0.0
11
1.0
21
1.0
12
558231.6831184776
22
6530351.842422694
13
0.0
23
0.0
14
0.5
24
0.5
15
0.5
25
0.5
16
0.0
26
0.0
36
1.0
17
0.0
27
0.0
37
0.0
40
29313.8120771577
41
1.310696095076
42
50.0
43
0.0
44
0.0
50
0.0
51
0.0
71
0
72
100
73
1
74
3
75
0
76
0
77
0
78
0
281
0
65
1
110
0.0
120
0.0
130
0.0
111
1.0
121
0.0
131
0.0
112
0.0
122
1.0
132
0.0
79
0
146
0.0
348
30C
60
3
61
5
292
0
282
1
141
0.0
142
0.0
63
250
421
3355443
361
329
0
ENDTAB
0
TABLE
2
LAYER
70
0
0
ENDTAB
0
ENDSEC
0
SECTION
2
BLOCKS
0
ENDSEC
0
SECTION
2
ENTITIES
"""
    for layer_name_raw, coord_text in placemark_data:
        clean_name = clean_layer_name(layer_name_raw)
        lines = [line.strip() for line in coord_text.split("\n") if line.strip()]
        try:
            points = [tuple(map(float, c.split(","))) for c in lines]
        except ValueError:
            continue
        projected = [transform(lon, lat) for lon, lat, *_ in points]
        if len(projected) > 1:
            dxf += f"""0
LWPOLYLINE
8
{clean_name}
90
{len(projected)}
70
1
38
0.0
"""
            for x, y in projected:
                dxf += f"""10
{x}
20
{y}
"""
        elif len(projected) == 1:
            x, y = projected[0]
            dxf += f"""0
POINT
8
{clean_name}
10
{x}
20
{y}
"""
    dxf += """0
ENDSEC
0
EOF
"""
    output_path = f"/kaggle/working/limoges_5{proj_name}.dxf"
    with open(output_path, "w") as f:
        f.write(dxf)
    dxf_outputs[proj_name] = output_path
