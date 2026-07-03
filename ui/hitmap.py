"""
HitMap — named clickable regions collected while a screen is drawn.
Renderer functions build one per frame; app.py hit-tests mouse clicks against it.
"""


class HitMap:
    def __init__(self):
        self._regions: list[tuple[str, tuple[int, int, int, int], int | None]] = []

    def add(self, name: str, rect: tuple[int, int, int, int], index: int | None = None):
        """Register a clickable rect (x1, y1, x2, y2). Later additions win on overlap."""
        self._regions.append((name, rect, index))

    def hit(self, x: int, y: int) -> tuple[str, int | None] | None:
        """Return (name, index) of the topmost region containing the point, or None."""
        for name, (x1, y1, x2, y2), index in reversed(self._regions):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return name, index
        return None
