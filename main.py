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
    output_path = f"/kaggle/working/limoges_{proj_name}.dxf"
    with open(output_path, "w") as f:
        f.write(dxf)
    dxf_outputs[proj_name] = output_path

dxf_outputs

