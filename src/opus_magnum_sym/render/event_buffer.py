from collections.abc import Iterator

from opus_magnum_sym.render.events import EventType, RenderEvent


class EventBuffer:
    def __init__(self) -> None:
        self._events: list[RenderEvent] = []

    def emit(
        self,
        event_type: EventType,
        r: int,
        s: int,
        value: int,
    ) -> None:
        self._events.append(
            RenderEvent(
                type=event_type,
                r=r,
                s=s,
                value=value,
            )
        )

    def clear(self) -> None:
        self._events.clear()

    def __iter__(self) -> Iterator[RenderEvent]:
        return iter(self._events)
