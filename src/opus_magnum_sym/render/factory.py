from opus_magnum_sym.render.null_renderer import NullRenderer
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.simulation.simulator import Simulator


def create_renderer(sim: Simulator, *, headless: bool = False) -> BoardRenderer | NullRenderer:
    """
    Create a renderer for the given simulator.

    Uses NullRenderer in headless mode and BoardRenderer otherwise.
    Pygame initialization happens only when BoardRenderer is instantiated.
    """
    if headless:
        return NullRenderer()
    return BoardRenderer(sim)
