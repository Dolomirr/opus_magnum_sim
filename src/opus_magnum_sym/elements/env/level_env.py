from opus_magnum_sym.elements.env.area_tracker import AreaTracker, default_area_tracker
from opus_magnum_sym.elements.env.index_manager import IndexManager, default_index_manager
from opus_magnum_sym.elements.env.level_counter import ResultCounter, default_result_counter


class LevelEnv:
    """
    Per-level environment state: one id allocator and one result counter.
    """

    def __init__(
        self,
        im: IndexManager | None = None,
        results: ResultCounter | None = None,
        area: AreaTracker | None = None,
    ) -> None:
        self.im = im if im is not None else IndexManager()
        self.results = results if results is not None else ResultCounter()
        self.area = area if area is not None else AreaTracker()

    def reset(self) -> None:
        self.im.reset()
        self.results.reset()
        self.area.reset()


# Module-level default env, sharing the default allocator and counter
# Preserved, so existing callers (and tests) that use no-env module functions preserve their behavior.
default_env = LevelEnv(
    im=default_index_manager,
    results=default_result_counter,
    area=default_area_tracker,
)
