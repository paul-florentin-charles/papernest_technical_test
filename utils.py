from pyproj import Transformer


def lambert93_to_gps(lon: float, lat: float):
    """
    Convert Lambert 93 (EPSG:2154) coordinates to WGS84 (longitude, latitude).
    """
    lambert = "+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
    wsg84 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

    return Transformer.from_crs(lambert, wsg84).transform(lon, lat)
