"""
MouseState — bridge between the OpenCV HighGUI mouse callback (which runs on
the GUI thread) and the main loop. deque append/popleft are atomic under the
GIL, so no lock is needed.

Wheel note (Qt HighGUI backend): EVENT_MOUSEWHEEL *is* delivered, with the
signed delta packed in the high 16 bits of `flags` (extracted manually below;
cv2.getMouseWheelDelta is not exposed in these Python bindings). The same
wheel-up event also triggers Qt's built-in viewport zoom-in, which cv2
exposes no API to disable — CTRL+Z resets it. That is why the menus
additionally offer clickable scrollbar arrows as a zoom-proof mouse scroll
path.
"""
from collections import deque

import cv2

# One wheel detent on a classic mouse; touchpads send smaller fractions.
_WHEEL_DETENT = 120


class MouseState:
    def __init__(self):
        self._clicks: deque[tuple[int, int]] = deque()
        self._wheel_accum: int = 0
        self.pos: tuple[int, int] = (-1, -1)

    def callback(self, event, x, y, flags, param):
        self.pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self._clicks.append((x, y))
        elif event in (cv2.EVENT_MOUSEWHEEL, cv2.EVENT_MOUSEHWHEEL):
            delta = (flags >> 16) & 0xffff  # signed short in the high word
            if delta >= 0x8000:
                delta -= 0x10000
            self._wheel_accum += delta

    def pop_clicks(self) -> list[tuple[int, int]]:
        clicks = []
        while self._clicks:
            clicks.append(self._clicks.popleft())
        return clicks

    def pop_scroll(self) -> int:
        """Whole wheel detents since the last call (positive = scroll up).
        Sub-detent remainders (smooth-scrolling touchpads) carry over."""
        ticks = int(self._wheel_accum / _WHEEL_DETENT)
        self._wheel_accum -= ticks * _WHEEL_DETENT
        return ticks
