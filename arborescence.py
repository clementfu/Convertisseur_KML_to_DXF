# la fonction build_folder_structure permet de voir toutes l'arborescence des placemarks dans les dossiers et sous dossiers sous forme de liste
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









def build_folder_structure(folder_elem):
    name_elem = folder_elem.find("kml:name", namespace)
    folder_name = name_elem.text.strip() if name_elem is not None else "Sans nom"

    structure = [folder_name]

    # Ajouter les placemarks de ce dossier
    placemarks = folder_elem.findall("kml:Placemark", namespace)
    for placemark in placemarks:
        placemark_name_elem = placemark.find("kml:name", namespace)
        placemark_name = placemark_name_elem.text.strip() if placemark_name_elem is not None else "Unknown"
        structure.append(placemark_name)

    # Recurse dans les sous-dossiers
    subfolders = folder_elem.findall("kml:Folder", namespace)
    for subfolder in subfolders:
        sub_structure = build_folder_structure(subfolder)
        structure.append(sub_structure)

    return structure

# Point de départ de l'arborescence (à partir de <Document>)
full_structure = []
top_folders = root.findall(".//kml:Document/kml:Folder", namespace)
for folder in top_folders:
    full_structure.append(build_folder_structure(folder))

# Pour visualiser :
import pprint
pprint.pprint(full_structure, width=100)





