# Network coverage by operator service

API service build with **FastAPI** exposing network coverage by operator.

## Running instructions

### Launch the API

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the API server using uvicorn:
   ```bash
   uvicorn main:app --reload
   ```
   By default, this will run the server at http://127.0.0.1:8000

### Open and test the API

- Open your browser and go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger UI.
- Alternatively, the OpenAPI schema is available at [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).

## API Endpoints to test

- `GET /network_coverage?addr=ADDRESS`
  - Returns network coverage (2G/3G/4G) by operator for a given address.
  - Example: `http://127.0.0.1:8000/network_coverage?addr=Av. Gustave Eiffel, 75007 Paris, France`

- `GET /address_from_gps_coords?lon=LONGITUDE&lat=LATITUDE`
  - Returns address information for given GPS coordinates.
  - Example: `http://127.0.0.1:8000/address_from_gps_coords?lon=2.2945&lat=48.8584`

---

For more details, see the API documentation at `/docs` after launching the server.

## Improvements

1. Use a simple YAML-like configuration to store path to CSV, operator codes & metrics
2. Use pydantic models to both:
   1. Validate upcoming data from "API adresse" of French government
   2. Uniformize data in API responses
3. Build some pipelines with GitHub Actions for linting, code coverage, type checking, etc.
4. Cache data from local CSV file smartly, e.g.:
   1. By storing directly converted coordinates to WSG 84.
   2. By storing a dict mapping operator to coordinates and network coverage.