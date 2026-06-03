"""
Pure landmark geometry functions.
All inputs are a single hand's landmark list (21 NormalizedLandmark items).
All distances are normalized to hand_scale (wrist → middle MCP distance).
"""
import math

# --- Landmark indices ---
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

# Finger (tip, mcp) pairs for the 4 main fingers (no thumb)
FINGER_PAIRS = [
    (INDEX_TIP, INDEX_MCP),
    (MIDDLE_TIP, MIDDLE_MCP),
    (RING_TIP, RING_MCP),
    (PINKY_TIP, PINKY_MCP),
]

# --- Tunable thresholds ---
THRESHOLDS = {
    'curl_extended': -0.15,   # curl value below this = finger is extended
    'curl_curled': 0.10,      # curl value above this = finger is curled
    'pinch_distance': 0.15,        # normalized distance for a pinch (thumb→index)
    'pinch_distance_middle': 0.18, # thumb→middle (finger is shorter, needs more headroom)
    'pinch_distance_ring':   0.20, # thumb→ring
    'pinch_distance_pinky':  0.22, # thumb→pinky (furthest, most lenient)
    'spread_distance': 0.25,  # normalized distance between adjacent tips for spread
    'tabletop_mcp_min': 70,   # degrees — MCP joint angle range for tabletop
    'tabletop_mcp_max': 110,
    'tabletop_pip_straight': 160,  # degrees — PIP/DIP angle for straight fingers
    'claw_pip_curled': 0.05,  # normalized y-drop at PIP for claw detection
    'claw_mcp_angle':  120,   # degrees — angle at MCP (WRIST→MCP→PIP); claw keeps MCPs extended (large angle)
}


def hand_scale(lm: list) -> float:
    """Euclidean distance from wrist (0) to middle MCP (9). Used as normalizer."""
    dx = lm[MIDDLE_MCP].x - lm[WRIST].x
    dy = lm[MIDDLE_MCP].y - lm[WRIST].y
    return math.sqrt(dx * dx + dy * dy) or 1.0  # avoid div/0


def orientation_sign(lm: list) -> float:
    """Returns +1 if hand is upright (wrist below middle MCP), -1 if inverted."""
    return 1.0 if lm[MIDDLE_MCP].y > lm[WRIST].y else -1.0


def finger_curl(lm: list, tip_idx: int, mcp_idx: int) -> float:
    """
    Normalized curl metric for a finger.
    Positive  → curled (tip is toward palm)
    Negative  → extended (tip is away from palm)
    Accounts for hand orientation (upright vs inverted in frame).
    """
    sign = orientation_sign(lm)
    raw = (lm[tip_idx].y - lm[mcp_idx].y) * sign
    return raw / hand_scale(lm)


def tip_distance(lm: list, idx_a: int, idx_b: int) -> float:
    """3D Euclidean distance between two landmarks, normalized by hand_scale.
    Includes the z coordinate (relative depth) to compensate for hand rotation."""
    dx = lm[idx_a].x - lm[idx_b].x
    dy = lm[idx_a].y - lm[idx_b].y
    dz = lm[idx_a].z - lm[idx_b].z
    return math.sqrt(dx * dx + dy * dy + dz * dz) / hand_scale(lm)


def angle_at_joint(lm: list, a: int, b: int, c: int) -> float:
    """
    Angle in degrees at landmark b, formed by vectors b→a and b→c.
    Returns a value in [0, 180].
    """
    ax, ay = lm[a].x - lm[b].x, lm[a].y - lm[b].y
    cx, cy = lm[c].x - lm[b].x, lm[c].y - lm[b].y
    dot = ax * cx + ay * cy
    mag_a = math.sqrt(ax * ax + ay * ay)
    mag_c = math.sqrt(cx * cx + cy * cy)
    if mag_a == 0 or mag_c == 0:
        return 0.0
    cos_angle = max(-1.0, min(1.0, dot / (mag_a * mag_c)))
    return math.degrees(math.acos(cos_angle))


def all_fingers_extended(lm: list) -> bool:
    """True if all 4 main fingers (index–pinky) are extended."""
    t = THRESHOLDS['curl_extended']
    return all(finger_curl(lm, tip, mcp) < t for tip, mcp in FINGER_PAIRS)


def all_fingers_curled(lm: list) -> bool:
    """True if all 4 main fingers (index–pinky) are curled."""
    t = THRESHOLDS['curl_curled']
    return all(finger_curl(lm, tip, mcp) > t for tip, mcp in FINGER_PAIRS)
