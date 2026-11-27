"""Simple event bus."""


class EventBus:
    def __init__(self):
        self._listeners = {}

    def on(self, event, cb):
        self._listeners.setdefault(event, []).append(cb)

    def off(self, event, cb):
        if event in self._listeners:
            self._listeners[event] = [c for c in self._listeners[event] if c is not cb]

    def emit(self, event, *a, **kw):
        for cb in list(self._listeners.get(event, [])):
            try:
                cb(*a, **kw)
            except Exception:  # noqa: BLE001, S110
                pass