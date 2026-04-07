"""
dms.py - Conversion between degrees-minutes-seconds (DMS) and decimal degrees (DD).

Functions:
    dms_to_dd(degrees, minutes, seconds, direction) -> float
    dd_to_dms(dd, axis)                             -> tuple[int, int, float, str]
"""


def dms_to_dd(degrees: int, minutes: int, seconds: float, direction: str = '') -> float:
    """Convert degrees, minutes, seconds to decimal degrees.

    Args:
        degrees:   Integer degrees (must be non-negative).
        minutes:   Integer minutes (0-59).
        seconds:   Seconds (0.0-60.0).
        direction: 'N', 'S', 'E', or 'W'. Result is negated for 'S' or 'W'.
                   Omit when signed decimal degrees are not needed.

    Returns:
        Decimal degrees (negative for S/W).

    Raises:
        ValueError: If arguments are out of range or direction is invalid.

    Example:
        >>> dms_to_dd(35, 40, 48, 'N')
        35.68
        >>> dms_to_dd(139, 46, 12, 'E')
        139.77
    """
    if degrees < 0:
        raise ValueError("degrees must be non-negative; use direction='S' or 'W' for negative values.")
    if not (0 <= minutes < 60):
        raise ValueError(f"minutes must be 0-59, got {minutes}.")
    if not (0.0 <= seconds < 60.0):
        raise ValueError(f"seconds must be 0.0-60.0, got {seconds}.")
    direction = direction.upper()
    if direction and direction not in ('N', 'S', 'E', 'W'):
        raise ValueError(f"direction must be N, S, E, or W, got '{direction}'.")

    dd = degrees + minutes / 60 + seconds / 3600
    if direction in ('S', 'W'):
        dd = -dd
    return round(dd, 10)


def dd_to_dms(dd: float, axis: str = '') -> tuple:
    """Convert decimal degrees to (degrees, minutes, seconds, direction).

    Args:
        dd:   Decimal degrees. Negative values are treated as S (latitude) or W (longitude).
        axis: 'lat' to append N/S, 'lon' to append E/W, '' to return empty direction string.

    Returns:
        (degrees, minutes, seconds, direction)
        seconds is rounded to 4 decimal places.

    Raises:
        ValueError: If axis is not 'lat', 'lon', or ''.

    Example:
        >>> dd_to_dms(35.68, axis='lat')
        (35, 40, 48.0, 'N')
        >>> dd_to_dms(-139.77, axis='lon')
        (139, 46, 12.0, 'W')
    """
    axis = axis.lower()
    if axis not in ('lat', 'lon', ''):
        raise ValueError(f"axis must be 'lat', 'lon', or '' (empty), got '{axis}'.")

    direction = ''
    if axis == 'lat':
        direction = 'N' if dd >= 0 else 'S'
    elif axis == 'lon':
        direction = 'E' if dd >= 0 else 'W'

    dd_abs = abs(dd)
    degrees = int(dd_abs)
    minutes_float = (dd_abs - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60, 4)

    return degrees, minutes, seconds, direction
