import os
import re
import xml.etree.ElementTree as ET
from pyproj import Transformer

# Charger le fichier KML
kml_file_path = "/kaggle/input/marseille/MARSEILLEPROVENCE-LFML-13L-31Rprincipale.kml"
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

        # Recherche robuste des coordonnées (peu importe la structure interne)
        coord_elem = placemark.find(".//kml:coordinates", namespace)
        if coord_elem is None:
            # si aucun, tenter sans namespace (au cas où)
            coord_elem = placemark.find(".//coordinates")
        if coord_elem is None:
            continue

        coordinates = coord_elem.text.strip()

        # Nom de calque basé sur le chemin : si appui/horizontale/conique présent => parent courant, sinon grand-parent
        if any(re.search(r"(appui|horizontale|conique)", part, re.IGNORECASE) for part in new_path):
            parent_layer = new_path[-1] if len(new_path) >= 1 else "SansNom"
        else:
            parent_layer = new_path[-2] if len(new_path) >= 2 else new_path[-1]

        # S'il y a "section", "divergence", "rac" ou "lat-" dans la hiérarchie -> prendre le dossier suivant (fils)
        for i in range(len(new_path) - 1):
            if any(word in new_path[i].lower() for word in ["section", "divergence", "rac", "lat-"]):
                parent_layer = new_path[i + 1]
                break

        # Fusion gauche/droite
        lowered = parent_layer.lower()
        if "gauche" in lowered or "droite" in lowered:
            parent_layer = re.sub(r'(?i)\b(gauche|droite)\b', '', parent_layer).strip()
            parent_layer += "_GD"

        # Préfixe OFZ si présent dans le chemin et pas déjà dans le nom de calque
        if any("OFZ" in part.upper() for part in new_path) and "OFZ" not in parent_layer.upper():
            parent_layer = "OFZ_" + parent_layer

        # Si parent_layer contient "Appui" (ou si dossier courant contient Appui) : règle spéciale:
        # (exemple demandé précédemment: prendre tous les dossiers fils, ici on garde la logique de nommage)
        # ... tu peux adapter ici si besoin.

        placemark_dict.setdefault(parent_layer, []).append(coordinates)

    # Recursion sur les sous-dossiers
    for subfolder in folder_elem.findall("kml:Folder", namespace):
        sub_dict = extract_grouped_placemarks(subfolder, new_path)
        for key, val in sub_dict.items():
            placemark_dict.setdefault(key, []).extend(val)

    return placemark_dict

# Extraction globale : certains KML ne placent pas les Folder sous Document de façon standard.
# On va chercher les Folder sous Document puis, à défaut, les Folder direct sous root.
placemark_groups = {}
top_folders = root.findall(".//kml:Document/kml:Folder", namespace)
if not top_folders:
    top_folders = root.findall(".//kml:Folder", namespace)

for top_folder in top_folders:
    grouped = extract_grouped_placemarks(top_folder, [])
    for key, val in grouped.items():
        placemark_groups.setdefault(key, []).extend(val)

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
    output_path = f"/kaggle/working/Marseille_2_{proj_name}.dxf"
    with open(output_path, "w") as f:
        f.write(dxf)
    dxf_outputs[proj_name] = output_path

dxf_outputs
