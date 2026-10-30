from collections.abc import Iterable


def cluster_key(exit_ids: Iterable[int]) -> frozenset[int]:
    """
    ID of cluster of connected *exits*.

    A "cluster" is full set of connected exits.
    Its key is a set of exit component ids, so every
    exit in the same cluster maps to the same counter.
    """
    return frozenset(exit_ids)


class ResultCounter:
    """
    Per-instance finished-molecule counter, keyed by exit cluster.
    """

    def __init__(self) -> None:
        self._finished: dict[frozenset[int], int] = {}
        self._finished_steps: dict[frozenset[int], list[int]] = {}

    def record_finished(self, exit_ids: Iterable[int], step: int | None = None) -> None:
        """
        Increment counter of the cluster identified by `exit_ids`.

        When `step` is given, also record the delivery step for that cluster.
        """
        key = cluster_key(exit_ids)
        self._finished[key] = self._finished.get(key, 0) + 1
        if step is not None:
            self._finished_steps.setdefault(key, []).append(step)

    def finished(self, exit_ids: Iterable[int]) -> int:
        """
        Finished count for the cluster identified by `exit_ids`.
        """
        return self._finished.get(cluster_key(exit_ids), 0)

    def finished_steps(self, exit_ids: Iterable[int]) -> list[int]:
        """
        Delivery steps for the cluster identified by `exit_ids`, in delivery order.
        """
        return list(self._finished_steps.get(cluster_key(exit_ids), []))

    def clusters(self) -> dict[frozenset[int], int]:
        """
        Snapshot of every cluster that has finished at least one molecule.
        """
        return dict(self._finished)

    def total_finished(self) -> int:
        """
        Total finished molecules across all clusters.
        """
        return sum(self._finished.values())

    def reset(self) -> None:
        """
        Clear every cluster counter.
        """
        self._finished.clear()
        self._finished_steps.clear()


# Module-level default instance.
# Preserved to keep exisintg callers working.
default_result_counter = ResultCounter()


def record_finished(exit_ids: Iterable[int], step: int | None = None) -> None:
    default_result_counter.record_finished(exit_ids, step=step)


def finished(exit_ids: Iterable[int]) -> int:
    return default_result_counter.finished(exit_ids)


def clusters() -> dict[frozenset[int], int]:
    return default_result_counter.clusters()


def total_finished() -> int:
    return default_result_counter.total_finished()


def reset() -> None:
    default_result_counter.reset()
