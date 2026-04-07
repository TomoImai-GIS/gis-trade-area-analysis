"""
mesh_code.py - JIS standard mesh code calculation for Japan (JIS X 0410).

Forward (coordinates → mesh code):
    to_mesh2(lat, lon)      -> str    6-digit secondary mesh code (~10 km grid)
    to_mesh3(lat, lon)      -> str    8-digit tertiary mesh code  (~1 km grid)

Inverse (mesh code → coordinates):
    mesh2_to_bbox(code)     -> dict   bounding box of a 6-digit mesh
    mesh2_to_center(code)   -> tuple  center (lat, lon) of a 6-digit mesh
    mesh3_to_bbox(code)     -> dict   bounding box of an 8-digit mesh
    mesh3_to_center(code)   -> tuple  center (lat, lon) of an 8-digit mesh

Ported from a JavaScript implementation originally used for internal GIS tooling.
"""

_LAT_MIN, _LAT_MAX = 20.0, 46.0
_LON_MIN, _LON_MAX = 122.0, 154.0


def _validate(lat: float, lon: float) -> None:
    if not (_LAT_MIN <= lat <= _LAT_MAX and _LON_MIN <= lon <= _LON_MAX):
        raise ValueError(
            f"Coordinates ({lat}, {lon}) are outside Japan's bounding box "
            f"(lat {_LAT_MIN}-{_LAT_MAX}, lon {_LON_MIN}-{_LON_MAX})."
        )


def to_mesh2(lat: float, lon: float) -> str:
    """Return the 6-digit JIS secondary mesh code for the given coordinates.

    Each secondary mesh covers approximately 7.5' latitude × 11.25' longitude
    (~10 km grid). Follows JIS X 0410.

    Args:
        lat: Latitude in decimal degrees (WGS84).
        lon: Longitude in decimal degrees (WGS84).

    Returns:
        6-digit mesh code string.

    Raises:
        ValueError: If coordinates are outside Japan's bounding box.

    Example:
        >>> to_mesh2(35.68, 139.77)
        '533946'
    """
    _validate(lat, lon)
    lat_s = lat * 1.5
    p = int(lat_s)
    q = int(8 * (lat_s - p))
    lon_s = lon - 100
    u = int(lon_s)
    v = int(8 * (lon_s - u))
    return f"{p:02d}{u:02d}{q}{v}"


def to_mesh3(lat: float, lon: float) -> str:
    """Return the 8-digit JIS tertiary mesh code for the given coordinates.

    Each tertiary mesh covers approximately 45'' latitude × 67.5'' longitude
    (~1 km grid). Follows JIS X 0410.

    Args:
        lat: Latitude in decimal degrees (WGS84).
        lon: Longitude in decimal degrees (WGS84).

    Returns:
        8-digit mesh code string.

    Raises:
        ValueError: If coordinates are outside Japan's bounding box.

    Example:
        >>> to_mesh3(35.68, 139.77)
        '53394611'
    """
    _validate(lat, lon)
    lat_s = lat * 1.5
    p = int(lat_s)
    lat_r = lat_s - p
    q = int(8 * lat_r)
    r = int(10 * (8 * lat_r - q))

    lon_s = lon - 100
    u = int(lon_s)
    lon_r = lon_s - u
    v = int(8 * lon_r)
    w = int(10 * (8 * lon_r - v))

    return f"{p:02d}{u:02d}{q}{v}{r}{w}"


# ---------------------------------------------------------------------------
# Inverse: mesh code → bounding box / center
# ---------------------------------------------------------------------------

def mesh2_to_bbox(code: str) -> dict:
    """Return the lat/lon bounding box of a 6-digit secondary mesh code.

    Args:
        code: 6-digit secondary mesh code (str or int).

    Returns:
        dict with keys: lat_min, lat_max, lon_min, lon_max (decimal degrees).

    Raises:
        ValueError: If code is not exactly 6 digits.

    Example:
        >>> mesh2_to_bbox('533946')
        {'lat_min': 35.666..., 'lat_max': 35.75, 'lon_min': 139.75, 'lon_max': 139.875}
    """
    code = str(code).strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"Secondary mesh code must be 6 digits, got '{code}'.")
    p, u, q, v = int(code[:2]), int(code[2:4]), int(code[4]), int(code[5])
    lat_min = (p + q / 8) / 1.5
    lat_max = (p + (q + 1) / 8) / 1.5
    lon_min = u + v / 8 + 100
    lon_max = u + (v + 1) / 8 + 100
    return {'lat_min': lat_min, 'lat_max': lat_max, 'lon_min': lon_min, 'lon_max': lon_max}


def mesh2_to_center(code: str) -> tuple:
    """Return the center (lat, lon) of a 6-digit secondary mesh code.

    Example:
        >>> mesh2_to_center('533946')
        (35.708..., 139.8125)
    """
    b = mesh2_to_bbox(code)
    return ((b['lat_min'] + b['lat_max']) / 2, (b['lon_min'] + b['lon_max']) / 2)


def mesh3_to_bbox(code: str) -> dict:
    """Return the lat/lon bounding box of an 8-digit tertiary mesh code.

    Args:
        code: 8-digit tertiary mesh code (str or int).

    Returns:
        dict with keys: lat_min, lat_max, lon_min, lon_max (decimal degrees).

    Raises:
        ValueError: If code is not exactly 8 digits.

    Example:
        >>> mesh3_to_bbox('53394611')
        {'lat_min': 35.675, 'lat_max': 35.683..., 'lon_min': 139.7625, 'lon_max': 139.775}
    """
    code = str(code).strip()
    if len(code) != 8 or not code.isdigit():
        raise ValueError(f"Tertiary mesh code must be 8 digits, got '{code}'.")
    p, u, q, v, r, w = (
        int(code[:2]), int(code[2:4]),
        int(code[4]), int(code[5]),
        int(code[6]), int(code[7])
    )
    lat_min = (p + q / 8 + r / 80) / 1.5
    lat_max = (p + q / 8 + (r + 1) / 80) / 1.5
    lon_min = u + v / 8 + w / 80 + 100
    lon_max = u + v / 8 + (w + 1) / 80 + 100
    return {'lat_min': lat_min, 'lat_max': lat_max, 'lon_min': lon_min, 'lon_max': lon_max}


def mesh3_to_center(code: str) -> tuple:
    """Return the center (lat, lon) of an 8-digit tertiary mesh code.

    Example:
        >>> mesh3_to_center('53394611')
        (35.679..., 139.76875)
    """
    b = mesh3_to_bbox(code)
    return ((b['lat_min'] + b['lat_max']) / 2, (b['lon_min'] + b['lon_max']) / 2)
