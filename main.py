import numpy as np 
import pandas as pd 
import os

import xml.etree.ElementTree as ET
from pyproj import Transformer
import re

# Charger le fichier KML
kml_file_path = "/kaggle/input/test-limoges/LIMOGESBELLEGARDE-LFBL-03-21principale.kml" #Avant lancement du code, mettre le bon chemin menant jusqu'au fichier KML (celui en Datasets si kaggle utilisé)
tree = ET.parse(kml_file_path)
root = tree.getroot()
namespace = {"kml": "http://www.opengis.net/kml/2.2"}

placemarks = root.findall(".//kml:Placemark", namespace)
folders = root.findall(".//kml:Folders", namespace)
coord_data = []
for placemark in placemarks:
    name = placemark.find("kml:name", namespace)
    coord_element = placemark.find(".//kml:coordinates", namespace)
    if coord_element is not None:
        coordinates = coord_element.text.strip()
        coord_data.append((name.text if name is not None else "Unknown", coordinates))

# Nettoyage des noms
def clean_layer_name(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

# Transformateurs pour WGS84 (identité) et Lambert 93
transformers = {
    "WGS84": lambda lon, lat: (lon, lat),
    "Lambert93": Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True).transform
}

# Création des fichiers DXF
dxf_outputs = {}
for projection_name, transform in transformers.items():
    dxf_content = """0  
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
    for name, coord_text in coord_data:
        clean_name = clean_layer_name(name)
        coord_lines = [line.strip() for line in coord_text.split("\n") if line.strip()]
        try:
            points = [tuple(map(float, coord.split(","))) for coord in coord_lines]
        except ValueError:
            continue
        projected_points = [transform(lon, lat) for lon, lat, _ in points]
        if len(projected_points) == 1:
            x, y = projected_points[0]
            dxf_content += f"""0
POINT
8
{clean_name}
10
{x}
20
{y}
30
0
"""
        else:
            dxf_content += f"""0
LWPOLYLINE
8
{clean_name}
90
{len(projected_points)}
"""
            for x, y in projected_points:
                dxf_content += f"""10
{x}
20
{y}
"""
            dxf_content += "70\n1\n"

    dxf_content += """0
ENDSEC
0
EOF
"""
    output_path = f"/kaggle/working/test_limoges{projection_name}.dxf" #définition du nom du fichier en sortie 
    with open(output_path, "w") as f:
        f.write(dxf_content)
    dxf_outputs[projection_name] = output_path

dxf_outputs
