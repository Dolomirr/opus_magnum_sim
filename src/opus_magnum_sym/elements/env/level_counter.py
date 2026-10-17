from collections.abc import Iterable


def cluster_key(exit_ids: Iterable[int]) -> frozenset[int]:
    """
    ID of cluster of connected *exits*.

    A "cluster" is full set of connected exits.
    Its key is a set of exit component ids, so every
    exit in the same cluster maps to the same counter.
    """
    return frozenset(exit_ids)


# Maps a cluster of connected exits to the number of molecules it has finished.
_finished: dict[frozenset[int], int] = {}


def record_finished(exit_ids: Iterable[int]) -> None:
    """
    Increment the counter of the cluster identified by `exit_ids`.
    """
    key = cluster_key(exit_ids)
    _finished[key] = _finished.get(key, 0) + 1


def finished(exit_ids: Iterable[int]) -> int:
    """
    Finished count for the cluster identified by `exit_ids`.
    """
    return _finished.get(cluster_key(exit_ids), 0)


def clusters() -> dict[frozenset[int], int]:
    """
    Snapshot of every cluster that has finished at least one molecule.
    """
    return dict(_finished)


def total_finished() -> int:
    """
    Total finished molecules across all clusters.
    """
    return sum(_finished.values())


def reset() -> None:
    """
    Clear every cluster counter.
    """
    _finished.clear()
