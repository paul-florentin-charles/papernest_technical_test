from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Query
from haversine import haversine

from utils import (
    MAX_ALLOWED_DISTANCE_KM,
    OPERATOR_NAME_BY_CODE,
    SATISFACTORY_DISTANCE_KM,
    load_operator_coverage_cache,
)

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
