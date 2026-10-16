from collections.abc import Iterable

from opus_magnum_sym.elements.env import level_counter


class Level:
    """
    Level-wide completion conditions.

    Targets map an exit cluster (a frozenset of connected exit component ids)
    to the minimum number of molecules that cluster must consume.
    """

    def __init__(self) -> None:
        self.targets: dict[frozenset[int], int] = {}

    def set_target(self, exit_ids: Iterable[int], count: int) -> None:
        """Require `count` finished molecules for the cluster identified by `exit_ids`."""
        if count < 0:
            raise ValueError("Target count must be non-negative")
        key = frozenset(exit_ids)
        if not key:
            raise ValueError("At least one exit id is required")
        self.targets[key] = count

    def is_satisfied(self) -> bool:
        """True when every defined target has been met."""
        if not self.targets:
            return False
        return all(level_counter.finished(cluster) >= target for cluster, target in self.targets.items())

    def reset(self) -> None:
        """Clear all targets."""
        self.targets.clear()
