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

# Extraction des placemarks groupés par dossier parent du dossier parent
def extract_grouped_placemarks(folder_elem, path):
    placemark_dict = {}

    name_elem = folder_elem.find("kml:name", namespace)
    folder_name = name_elem.text.strip() if name_elem is not None else "SansNom"
    new_path = path + [folder_name]

    for placemark in folder_elem.findall("kml:Placemark", namespace):
        placemark_name_elem = placemark.find("kml:name", namespace)
        placemark_name = placemark_name_elem.text.strip() if placemark_name_elem is not None else "Unknown"

        # Ignore les cotations
        if "cotation" in placemark_name.lower():
            continue

        coordinates_elem = placemark.find(".//kml:coordinates", namespace)
        if coordinates_elem is not None:
            coordinates = coordinates_elem.text.strip()
            # Utilise le dossier parent du parent (avant-dernier)
            parent_layer = new_path[-2] if len(new_path) >= 2 else new_path[-1]
            if parent_layer not in placemark_dict:
                placemark_dict[parent_layer] = []
            placemark_dict[parent_layer].append(coordinates)

    for subfolder in folder_elem.findall("kml:Folder", namespace):
        sub_dict = extract_grouped_placemarks(subfolder, new_path)
        for key, val in sub_dict.items():
            placemark_dict.setdefault(key, []).extend(val)

    return placemark_dict

# Extraction globale
placemark_groups = {}
for top_folder in root.findall(".//kml:Document/kml:Folder", namespace):
    grouped = extract_grouped_placemarks(top_folder, [])
    for key, val in grouped.items():
        placemark_groups.setdefault(key, []).extend(val)

# Projections
transformers = {
    "WGS84": lambda lon, lat: (lon, lat),
    "Lambert93": Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True).transform
}

# Génération DXF
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
LAYER
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

    for raw_layer, coord_list in placemark_groups.items():
        clean_name = clean_layer_name(raw_layer)
        for coord_text in coord_list:
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
    output_path = f"/kaggle/working/limoges_7{proj_name}.dxf"
    with open(output_path, "w") as f:
        f.write(dxf)
    dxf_outputs[proj_name] = output_path

dxf_outputs
