import json
import math
import os
from collections import defaultdict
from typing import Any

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, Query
from haversine import haversine

from utils import lambert93_to_wsg84

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


app = FastAPI(
    title="Mobile Network Coverage API",
    description="API to query mobile network coverage by operator and technology (2G/3G/4G) for a given address using French government open data.",
    version="1.0.0",
)


@app.get(
    "/network_coverage",
    summary="Get network coverage (2G/3G/4G) by operator for a given address",
    description="Returns the closest coverage sites of each operator for the given address.",
)
def get_network_coverage(
    addr: str = Query(
        ...,
        description="Address to search network coverage for (e.g. 'Av. Gustave Eiffel, 75007 Paris, France')",
    ),
):
    resp = requests.get(f"https://api-adresse.data.gouv.fr/search/?q={addr}")
    resp.raise_for_status()

    features = resp.json().get("features")
    if not features:
        raise HTTPException(status_code=404, detail="Address not found")

    coords: tuple[float, float] = features[0]["geometry"][
        "coordinates"
    ]  # [longitude, latitude]
    api_lon, api_lat = coords[0], coords[1]

    operator_best: dict[str, dict] = {}
    for operator_code, entries in load_operator_coverage_cache().items():
        try:
            operator_name = OPERATOR_NAME_BY_CODE[int(operator_code)]
        except ValueError:
            raise ValueError(
                f"Operator code should be an int or numeric string in CSV, we were given: {operator_code}."
            )
        except KeyError:
            raise KeyError(
                f"Unknown operator code in CSV: {operator_code}, it should belong to {OPERATOR_NAME_BY_CODE.keys()}."
            )

        for entry in entries:
            entry_coords: dict[str, float] = entry["csv_coords_gps"]
            distance = haversine(
                (api_lat, api_lon), (entry_coords["lat"], entry_coords["lon"])
            )
            if distance > MAX_ALLOWED_DISTANCE_KM:
                continue

            if operator_name in operator_best:
                if distance < operator_best[operator_name]["distance_km"] > distance:
                    operator_best[operator_name] = {
                        "distance_km": distance,
                        "csv_coords_gps": entry["csv_coords_gps"],
                        "coverage": entry["coverage"],
                    }
            else:
                operator_best[operator_name] = {
                    "distance_km": distance,
                    "csv_coords_gps": entry["csv_coords_gps"],
                    "coverage": entry["coverage"],
                }

            if distance <= SATISFACTORY_DISTANCE_KM:
                break  # Found a good enough distance, move to next operator

    if not operator_best:
        raise HTTPException(
            status_code=404,
            detail=f"No coverage data found within {MAX_ALLOWED_DISTANCE_KM} km for any provider",
        )

    return operator_best


@app.get(
    "/address_from_wsg84",
    summary="Returns address information for given WGS 84 coordinates.",
    description="Returns address information for given longitude and latitude. "
    "Useful for checking the best coordinate fits from the coverage endpoint.",
)
def get_address_from_wsg84(
    lon: float = Query(..., description="Longitude in decimal degrees (WGS 84)"),
    lat: float = Query(..., description="Latitude in decimal degrees (WGS 84)"),
):
    resp = requests.get(
        f"https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}"
    )
    resp.raise_for_status()

    features = resp.json().get("features")
    if not features:
        raise HTTPException(
            status_code=404, detail="No address found for these coordinates"
        )

    # Get properties from the best fit
    properties: dict[str, Any] = features[0]["properties"]

    # Return selected fields if available
    return {
        k: properties.get(k)
        for k in [
            "city",
            "context",
            "label",
            "name",
            "postcode",
            "street",
        ]
        if k in properties
    }
