import os
import re
import xml.etree.ElementTree as ET
from pyproj import Transformer

# Charger le fichier KML
kml_file_path = "/kaggle/input/visuols-mars/VISUOLS_Marseille.kml"
tree = ET.parse(kml_file_path)
root = tree.getroot()

# Détecter dynamiquement le namespace KML utilisé dans le fichier
if root.tag.startswith("{"):
    ns_uri = root.tag.split("}")[0].strip("{")
else:
    ns_uri = "http://www.opengis.net/kml/2.2"  # fallback
namespace = {"kml": ns_uri}

# Nettoyage des noms de calque
def clean_layer_name(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

def extract_grouped_placemarks(folder_elem, path):
    placemark_dict = {}

    name_elem = folder_elem.find("kml:name", namespace)
    folder_name = name_elem.text.strip() if name_elem is not None else "SansNom"
    new_path = path + [folder_name]

    # Parcours des placemarks directs du dossier
    for placemark in folder_elem.findall("kml:Placemark", namespace):
        placemark_name_elem = placemark.find("kml:name", namespace)
        placemark_name = placemark_name_elem.text.strip() if placemark_name_elem is not None else "Unknown"

        # Ignore les cotations
        if "cotation" in placemark_name.lower():
            continue

        # Recherche robuste des coordonnées
        coord_elem = placemark.find(".//kml:coordinates", namespace)
        if coord_elem is None:
            coord_elem = placemark.find(".//coordinates")
        if coord_elem is None:
            continue

        coordinates = coord_elem.text.strip()

        # Règle de nommage du parent
        if any(re.search(r"(appui|horizontale|conique|conical|horizontal|strip|clearway)", part, re.IGNORECASE) for part in new_path):
            parent_layer = new_path[-1] if len(new_path) >= 1 else "SansNom"           
        else:
            parent_layer = new_path[-2] if len(new_path) >= 2 else new_path[-1]

        # Cas section/divergence/rac/lat-
        for i in range(len(new_path) - 1):
            if any(word in new_path[i].lower() for word in ["section", "divergence", "rac", "lat-"]):
                parent_layer = new_path[i + 1]
                break

        # Préfixes OLD / NEW
        if any("OLDOLS" in part.upper() for part in new_path):
            parent_layer = "OLD_" + parent_layer
        elif any("NEWOLS" in part.upper() for part in new_path):
            parent_layer = "NEW_" + parent_layer

        # Fusion gauche/droite
        lowered = parent_layer.lower()
        if "gauche" in lowered or "droite" in lowered:
            parent_layer = re.sub(r'(?i)\b(gauche|droite)\b', '', parent_layer).strip()
            parent_layer += "_GD"
        if "left" in lowered or "right" in lowered:
            parent_layer = re.sub(r'(?i)\b(left|right)\b', '', parent_layer).strip()
            parent_layer += "_LR"

        # Préfixe OFZ si présent
        if any("OFZ" in part.upper() for part in new_path) and "OFZ" not in parent_layer.upper():
            parent_layer = "OFZ_" + parent_layer

        placemark_dict.setdefault(parent_layer, []).append(coordinates)

    # Recursion sur les sous-dossiers
    for subfolder in folder_elem.findall("kml:Folder", namespace):
        sub_dict = extract_grouped_placemarks(subfolder, new_path)
        for key, val in sub_dict.items():
            placemark_dict.setdefault(key, []).extend(val)

    return placemark_dict

# Extraction globale
placemark_groups = {}
top_folders = root.findall(".//kml:Document/kml:Folder", namespace)
if not top_folders:
    top_folders = root.findall(".//kml:Folder", namespace)

for top_folder in top_folders:
    grouped = extract_grouped_placemarks(top_folder, [])
    for key, val in grouped.items():
        placemark_groups.setdefault(key, []).extend(val)

# Renommage final des calques
final_layer_rename = {
    "AERODROME": "Runway",
    "NEW_NEWOLS": "NEW_Runway_Surface"
    # ajouter d'autres renoms si besoin
}

renamed_groups = {}
for layer_name, coords in placemark_groups.items():
    new_name = final_layer_rename.get(layer_name, layer_name)
    renamed_groups[new_name] = coords

placemark_groups = renamed_groups

# Transformations (projections)
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
    output_path = f"/kaggle/working/Marseille_9_{proj_name}.dxf"
    with open(output_path, "w") as f:
        f.write(dxf)
    dxf_outputs[proj_name] = output_path

dxf_outputs
