from opus_magnum_sym.elements.atoms.atom import Atom


def collect_molecule(root: Atom) -> set[Atom]:
    """
    All atoms reachable from `root` via connections, `root` included.
    """
    visited = {root}
    queue = [root]
    while queue:
        atom = queue.pop()
        for _, neighbor in atom.iter_connections():
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited
