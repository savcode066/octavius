"""Object width -> claw angle, and the tunable numbers for pick up / put down.

Settings are read from the environment on every call so a `.env` edit only
needs a restart and tests can override them. Angles are servo degrees: the claw
is inverted, so a higher angle opens it and a lower angle closes it.
"""
import math
import os

DEFAULTS = {
    "OCTAVIUS_CLAW_NARROW_CM": 7.0,
    "OCTAVIUS_CLAW_NARROW_ANGLE": 80.0,
    "OCTAVIUS_CLAW_WIDE_CM": 9.0,
    "OCTAVIUS_CLAW_WIDE_ANGLE": 85.0,
    "OCTAVIUS_GRIP_MARGIN_DEG": 0.0,
    "OCTAVIUS_PICKUP_PITCH": 0.0,
    "OCTAVIUS_PUTDOWN_PITCH": 110.0,
    "OCTAVIUS_CLAW_OPEN_ANGLE": 110.0,
}

def setting(name):
    raw = os.getenv(name, "").strip()
    if not raw:
        return DEFAULTS[name]
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} in .env must be a number.") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} in .env must be a number.")
    return value

def width_to_claw_angle(width_cm):
    """Interpolate between the two calibrated (width, angle) points."""
    if (isinstance(width_cm, bool) or not isinstance(width_cm, (int, float))
            or not math.isfinite(width_cm)):
        raise ValueError("Enter the object width in cm.")
    narrow_cm, wide_cm = setting("OCTAVIUS_CLAW_NARROW_CM"), setting("OCTAVIUS_CLAW_WIDE_CM")
    narrow_angle, wide_angle = setting("OCTAVIUS_CLAW_NARROW_ANGLE"), setting("OCTAVIUS_CLAW_WIDE_ANGLE")
    if narrow_cm >= wide_cm:
        raise ValueError("Claw calibration is invalid: the narrow width must be smaller than the wide width.")
    if not narrow_cm <= width_cm <= wide_cm:
        raise ValueError(f"Object width must be between {narrow_cm:g} and {wide_cm:g} cm, "
                         "the range the claw is calibrated for.")
    fraction = (width_cm - narrow_cm) / (wide_cm - narrow_cm)
    angle = narrow_angle + fraction * (wide_angle - narrow_angle) - setting("OCTAVIUS_GRIP_MARGIN_DEG")
    return max(0, min(180, math.floor(angle + 0.5)))
