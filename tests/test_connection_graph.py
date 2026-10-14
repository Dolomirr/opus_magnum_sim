from opus_magnum_sym.elements.components.connections import ConnectionGraph


def test_add_and_links_of():
    graph = ConnectionGraph()
    graph.add(1, 2)

    assert graph.links_of(1) == {2}
    assert graph.links_of(2) == {1}


def test_remove_link():
    graph = ConnectionGraph()
    graph.add(1, 2)
    graph.add(2, 3)
    graph.remove(1, 2)

    assert graph.links_of(1) == set()
    assert graph.links_of(2) == {3}


def test_remove_component_purges_all_links():
    graph = ConnectionGraph()
    graph.add(1, 2)
    graph.add(1, 3)
    graph.remove_component(1)

    assert graph.links_of(1) == set()
    assert graph.links_of(2) == set()
    assert graph.links_of(3) == set()


def test_group_of_direct_and_transitive():
    graph = ConnectionGraph()
    graph.add(1, 2)
    graph.add(2, 3)

    assert graph.group_of(1) == {1, 2, 3}
    assert graph.group_of(2) == {1, 2, 3}
    assert graph.group_of(3) == {1, 2, 3}


def test_group_of_isolated_component():
    graph = ConnectionGraph()

    assert graph.group_of(7) == {7}


def test_two_separate_groups_are_disjoint():
    graph = ConnectionGraph()
    graph.add(1, 2)
    graph.add(3, 4)

    assert graph.group_of(1) == {1, 2}
    assert graph.group_of(3) == {3, 4}
    assert graph.group_of(1).isdisjoint(graph.group_of(3))
