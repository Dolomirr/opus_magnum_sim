from opus_magnum_sym.simulation.simulator import Simulator


class NullRenderer:
    """
    Headless renderer that does nothing.

    Drop-in replacement for BoardRenderer when no display is available
    or desired. All drawing/event methods are no-ops.
    """

    def __init__(self, simulator: Simulator | None = None) -> None:
        pass

    def draw(self) -> None:
        pass

    def tick(self, fps: int = 60) -> None:
        pass

    def process_events(self) -> bool:
        return True
