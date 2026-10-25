"""
Simulation runtime errors.
"""

from opus_magnum_sym.simulation.collision import CollisionEvent


class SimulationRuntimeError(Exception):
    def __init__(self, message: str, step: int) -> None:
        self.message = message
        super().__init__(message)


class SimulationCollisionError(SimulationRuntimeError):
    """
    Raised on spatial collision during a step.
    """

    def __init__(self, event: CollisionEvent) -> None:
        self.event = event
        self.step = event.step
        super().__init__(self._format(event), step=event.step)

    @staticmethod
    def _format(event: CollisionEvent) -> str:
        owners = ", ".join(str(i) for i in event.owner_ids)
        return (
            f"{event.category.name} collision at step {event.step} "
            f"near ({event.cell.r}, {event.cell.s}) by component {owners}"
        )
