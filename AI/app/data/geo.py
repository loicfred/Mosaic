"""Zip-prefix centroids and great-circle distance."""
import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0


def zip_centroids(geolocation: pd.DataFrame) -> pd.DataFrame:
    """Mean latitude/longitude per zip prefix, indexed by prefix."""
    return (
        geolocation.groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]]
        .mean()
        .rename(columns={"geolocation_lat": "lat", "geolocation_lng": "lng"})
    )


def haversine_km(lat1, lng1, lat2, lng2):
    """Vectorised great-circle distance; NaN propagates when any coordinate is missing."""
    lat1, lng1, lat2, lng2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))
