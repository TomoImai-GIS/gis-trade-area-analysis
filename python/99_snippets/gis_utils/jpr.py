"""
jpr.py - Conversion between WGS84 and Japan Plane Rectangular Coordinate System.

Requires: pyproj >= 2.2  (pip install pyproj)

Japan Plane Rectangular Coordinate System (平面直角座標系) has 19 zones (I-XIX),
defined in JGD2011 (EPSG:6669-6687). Each zone uses a local origin in metres.

Axis convention (Japan standard):
    X = northing  (positive = north of origin)
    Y = easting   (positive = east of origin)

Functions:
    wgs84_to_jpr(lat, lon, zone) -> tuple[float, float]   WGS84 → (X, Y) in metres
    jpr_to_wgs84(x, y, zone)     -> tuple[float, float]   (X, Y) → (lat, lon)
    get_zone(prefecture)         -> int                    prefecture name → zone number
"""

try:
    from pyproj import Transformer
except ImportError as e:
    raise ImportError(
        "pyproj is required for JPR conversion: pip install pyproj"
    ) from e

# Zone number (1-19) → EPSG code (JGD2011 / Japan Plane Rectangular)
_ZONE_EPSG = {i: 6668 + i for i in range(1, 20)}

# Prefecture name (kanji or lowercase romaji) → recommended zone
# Notes:
#   - Hokkaido spans zones 11-13 by area; zone 12 is returned as the main-area default.
#   - Tokyo remote islands (Ogasawara/Iwo Jima) belong to zone 14, not 9.
#   - Okinawa remote islands (Miyako, Yaeyama) belong to zone 16-18, not 15.
_PREF_ZONE: dict[str, int] = {
    # Zone I — Nagasaki (main island groups)
    '長崎': 1,   'nagasaki': 1,
    # Zone II — northern Kyushu, Kagoshima
    '福岡': 2,   'fukuoka': 2,   '大分': 2,  'oita': 2,
    '宮崎': 2,   'miyazaki': 2,  '鹿児島': 2, 'kagoshima': 2,
    # Zone III — western Chugoku
    '山口': 3,   'yamaguchi': 3, '島根': 3,  'shimane': 3,  '広島': 3,  'hiroshima': 3,
    # Zone IV — Shikoku
    '香川': 4,   'kagawa': 4,    '愛媛': 4,  'ehime': 4,
    '徳島': 4,   'tokushima': 4, '高知': 4,  'kochi': 4,
    # Zone V — eastern Chugoku, Hyogo
    '兵庫': 5,   'hyogo': 5,     '鳥取': 5,  'tottori': 5,  '岡山': 5,  'okayama': 5,
    # Zone VI — Kinki
    '京都': 6,   'kyoto': 6,     '大阪': 6,  'osaka': 6,
    '福井': 6,   'fukui': 6,     '滋賀': 6,  'shiga': 6,
    '三重': 6,   'mie': 6,       '奈良': 6,  'nara': 6,     '和歌山': 6, 'wakayama': 6,
    # Zone VII — Chubu (west)
    '石川': 7,   'ishikawa': 7,  '富山': 7,  'toyama': 7,
    '岐阜': 7,   'gifu': 7,      '愛知': 7,  'aichi': 7,
    # Zone VIII — Chubu (east)
    '新潟': 8,   'niigata': 8,   '長野': 8,  'nagano': 8,
    '山梨': 8,   'yamanashi': 8, '静岡': 8,  'shizuoka': 8,
    # Zone IX — Kanto, Tohoku south
    '東京': 9,   'tokyo': 9,     '福島': 9,  'fukushima': 9,
    '栃木': 9,   'tochigi': 9,   '茨城': 9,  'ibaraki': 9,
    '埼玉': 9,   'saitama': 9,   '千葉': 9,  'chiba': 9,
    '神奈川': 9, 'kanagawa': 9,  '山形': 9,  'yamagata': 9,
    '群馬': 9,   'gunma': 9,
    # Zone X — Tohoku north
    '青森': 10,  'aomori': 10,   '秋田': 10, 'akita': 10,
    '岩手': 10,  'iwate': 10,    '宮城': 10, 'miyagi': 10,
    # Zone XI — southwest Hokkaido
    # Zone XII — central Hokkaido (main area default)
    '北海道': 12, 'hokkaido': 12,
    # Zone XIII — eastern Hokkaido
    # Zone XIV — Ogasawara / Iwo Jima (Tokyo remote islands)
    # Zone XV — Okinawa main island
    '沖縄': 15,  'okinawa': 15,
    # Zone XVI-XVIII — Okinawa remote islands (omitted: use zone number directly)
}


def get_zone(prefecture: str) -> int:
    """Return the recommended JPR zone number for a given prefecture.

    Args:
        prefecture: Prefecture name in kanji (e.g. '東京') or lowercase romaji (e.g. 'tokyo').

    Returns:
        Zone number (1-19).

    Raises:
        KeyError: If the prefecture name is not recognized.

    Note:
        For Hokkaido, zone 12 is returned (covers the main area).
        For Tokyo remote islands or Okinawa remote islands, specify the zone directly.

    Example:
        >>> get_zone('東京')
        9
        >>> get_zone('osaka')
        6
    """
    key = prefecture if ord(prefecture[0]) > 0x7F else prefecture.lower()
    if key not in _PREF_ZONE:
        raise KeyError(
            f"Prefecture '{prefecture}' not found. "
            "Use kanji (e.g. '東京') or lowercase romaji (e.g. 'tokyo')."
        )
    return _PREF_ZONE[key]


def wgs84_to_jpr(lat: float, lon: float, zone: int) -> tuple:
    """Convert WGS84 geographic coordinates to Japan Plane Rectangular (X, Y).

    Args:
        lat:  Latitude in decimal degrees (WGS84).
        lon:  Longitude in decimal degrees (WGS84).
        zone: JPR zone number (1-19).

    Returns:
        (X, Y) in metres. X = northing, Y = easting.
        Negative X means south of the zone origin; negative Y means west.

    Raises:
        ValueError: If zone is not in 1-19.

    Example:
        >>> x, y = wgs84_to_jpr(35.6812, 139.7671, zone=9)  # Tokyo Station
        >>> round(x), round(y)  # northing, easting (metres from zone IX origin)
        (-35367, -5995)
    """
    if zone not in _ZONE_EPSG:
        raise ValueError(f"zone must be 1-19, got {zone}.")
    t = Transformer.from_crs("EPSG:4326", f"EPSG:{_ZONE_EPSG[zone]}", always_xy=False)
    return t.transform(lat, lon)


def jpr_to_wgs84(x: float, y: float, zone: int) -> tuple:
    """Convert Japan Plane Rectangular (X, Y) coordinates to WGS84.

    Args:
        x:    Northing in metres (X coordinate in JPR convention).
        y:    Easting in metres (Y coordinate in JPR convention).
        zone: JPR zone number (1-19).

    Returns:
        (lat, lon) in decimal degrees (WGS84).

    Raises:
        ValueError: If zone is not in 1-19.

    Example:
        >>> lat, lon = jpr_to_wgs84(-35367, -5995, zone=9)
        >>> round(lat, 4), round(lon, 4)
        (35.6812, 139.7671)
    """
    if zone not in _ZONE_EPSG:
        raise ValueError(f"zone must be 1-19, got {zone}.")
    t = Transformer.from_crs(f"EPSG:{_ZONE_EPSG[zone]}", "EPSG:4326", always_xy=False)
    return t.transform(x, y)
