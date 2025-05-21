import json
import math
import os
from collections import defaultdict

import pandas as pd
from pyproj import Transformer

# Location of CSV file mapping operator and coordinates to network coverage
CSV_PATH = os.path.join(
    "resources", "2018_01_Sites_mobiles_2G_3G_4G_France_metropolitaine_L93.csv"
)

# Operator name by its code (MCC + MNC)
# Source: https://fr.wikipedia.org/wiki/Mobile_Network_Code#Tableau_des_MNC_pour_la_France_m%C3%A9tropolitaine
OPERATOR_NAME_BY_CODE: dict[int, str] = {
    20801: "Orange",
    20810: "SFR",
    20815: "Free",
    20820: "Bouygues",
}
ALL_KNOWN_OPERATOR: set[str] = set(OPERATOR_NAME_BY_CODE.values())

# Coverage area limits
MAX_ALLOWED_DISTANCE_KM = 20.0  # over this distance, we ignore coverage
SATISFACTORY_DISTANCE_KM = 5.0  # "big" city radius, coverage is good enough

# --- CSV cache for operator code to list of coverage dicts ---
CACHE_FILE_PATH = os.path.join("cache", "operator_coverage_cache.json")


def lambert93_to_wsg84(lon: float, lat: float):
    """
    Convert Lambert 93 (EPSG:2154) coordinates to WGS84 (longitude, latitude).
    """
    lambert = "+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
    wsg84 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

    return Transformer.from_crs(lambert, wsg84).transform(lon, lat)


def load_operator_coverage_cache():
    # Try loading existing cache file first
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    data_to_cache: dict[str, list[dict]] = defaultdict(list)
    for row in pd.read_csv(CSV_PATH, dtype=str, sep=";", encoding="utf-8").to_dict(
        orient="records"
    ):
        x, y = row["x"], row["y"]
        try:
            x = float(x)
            y = float(y)
            if math.isnan(x) or math.isnan(y):
                continue
        except (ValueError, TypeError):
            continue

        lon, lat = lambert93_to_wsg84(x, y)
        coverage = {
            "2G": bool(int(row["2G"])),
            "3G": bool(int(row["3G"])),
            "4G": bool(int(row["4G"])),
        }

        data_to_cache[row["Operateur"]].append(
            {
                "csv_coords_lambert93": {"lon": x, "lat": y},
                "csv_coords_gps": {"lon": lon, "lat": lat},
                "coverage": coverage,
            }
        )

    # Save cache as JSON file while creating directory if not existing
    os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
    with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data_to_cache, f)

    return data_to_cache
