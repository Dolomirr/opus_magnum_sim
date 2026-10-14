class ConnectionGraph:
    """
    Undirected link graph between component ids.
    Pure-id, contain no board or component knowledge.
    """

    def __init__(self) -> None:
        self._adj: dict[int, set[int]] = {}

    def add(self, a: int, b: int) -> None:
        self._adj.setdefault(a, set()).add(b)
        self._adj.setdefault(b, set()).add(a)

    def remove(self, a: int, b: int) -> None:
        if a in self._adj:
            self._adj[a].discard(b)
            if not self._adj[a]:
                del self._adj[a]
        if b in self._adj:
            self._adj[b].discard(a)
            if not self._adj[b]:
                del self._adj[b]

    def remove_component(self, a: int) -> None:
        """
        Purge every link incident to `a`.
        """
        neighbors = self._adj.pop(a, set())
        for neighbor in neighbors:
            if neighbor in self._adj:
                self._adj[neighbor].discard(a)
                if not self._adj[neighbor]:
                    del self._adj[neighbor]

    def links_of(self, a: int) -> set[int]:
        """
        Direct neighbours of `a`.
        """
        return set(self._adj.get(a, ()))

    def group_of(self, a: int) -> set[int]:
        """
        Transitive closure over adjacency, `a` included.
        """
        if a not in self._adj:
            return {a}
        visited = {a}
        queue = [a]
        while queue:
            node = queue.pop()
            for neighbor in self._adj.get(node, ()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited
