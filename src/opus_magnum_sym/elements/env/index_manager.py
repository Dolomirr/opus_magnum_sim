class IndexManager:
    """
    Per-instance allocator for component ids, independent of any other envs.
    """

    def __init__(self) -> None:
        self._next_id: int = 0
        self._active: set[int] = set()
        self._free: set[int] = set()

    def allocate(self) -> int:
        idx = self._free.pop() if self._free else self._next_id
        if idx == self._next_id:
            self._next_id += 1
        self._active.add(idx)
        return idx

    def free(self, idx: int) -> None:
        if idx not in self._active:
            msg = f"Index {idx} is not currently active."
            raise ValueError(msg)
        self._active.remove(idx)
        self._free.add(idx)

    def is_active(self, idx: int) -> bool:
        return idx in self._active

    def is_valid(self, idx: int) -> bool:
        return idx >= 0 and idx < self._next_id

    def active_count(self) -> int:
        return len(self._active)

    def total_allocated(self) -> int:
        return self._next_id

    def get_all_active(self) -> set[int]:
        return self._active.copy()

    def reset(self) -> None:
        self._next_id = 0
        self._active.clear()
        self._free.clear()


# Module-level default instance.
# Preserved, so existing callers (and tests) keep working.
default_index_manager = IndexManager()
# Sloppy, but no way i am fixing all these "tests".


def allocate() -> int:
    return default_index_manager.allocate()


def free(idx: int) -> None:
    default_index_manager.free(idx)


def is_active(idx: int) -> bool:
    return default_index_manager.is_active(idx)


def is_valid(idx: int) -> bool:
    return default_index_manager.is_valid(idx)


def active_count() -> int:
    return default_index_manager.active_count()


def total_allocated() -> int:
    return default_index_manager.total_allocated()


def get_all_active() -> set[int]:
    return default_index_manager.get_all_active()


def reset() -> None:
    default_index_manager.reset()
