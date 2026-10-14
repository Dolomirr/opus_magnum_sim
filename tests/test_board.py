import numpy as np
import pytest

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Board, Direction, Hex
from opus_magnum_sym.elements.components import ComponentType


def test_place_and_get_atom():
    board = Board(3, 3)
    atom = Atom(AtomType.BASIC)

    assert board.place_atom(Hex(1, 1), atom) is True
    assert board.get_atom(Hex(1, 1)) is atom


def test_place_atom_rejects_occupied_and_out_of_bounds():
    board = Board(2, 2)

    assert board.place_atom(Hex(1, 1), Atom(AtomType.BASIC)) is True
    assert board.place_atom(Hex(1, 1), Atom(AtomType.BASIC)) is False
    assert board.place_atom(Hex(5, 5), Atom(AtomType.BASIC)) is False


def test_remove_atom_returns_and_empties():
    board = Board(3, 3)
    atom = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 1), atom)

    assert board.remove_atom(Hex(1, 1)) is atom
    assert board.get_atom(Hex(1, 1)) is None
    assert board.remove_atom(Hex(1, 1)) is None


def test_move_atom_preserves_instance():
    board = Board(3, 3)
    atom = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), atom)

    assert board.move_atom(Hex(0, 0), Hex(2, 2)) is True
    assert board.get_atom(Hex(0, 0)) is None
    assert board.get_atom(Hex(2, 2)) is atom


def test_move_atom_failure_leaves_board_untouched():
    board = Board(3, 3)
    atom = Atom(AtomType.BASIC)
    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), atom)
    board.place_atom(Hex(2, 2), blocker)

    assert board.move_atom(Hex(0, 0), Hex(2, 2)) is False  # dst occupied
    assert board.move_atom(Hex(1, 1), Hex(2, 0)) is False  # empty src
    assert board.move_atom(Hex(0, 0), Hex(9, 9)) is False  # dst out of bounds

    assert board.get_atom(Hex(0, 0)) is atom
    assert board.get_atom(Hex(2, 2)) is blocker


def test_connections_survive_move():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    a.connect(1, b)

    board.place_atom(Hex(0, 0), a)
    board.move_atom(Hex(0, 0), Hex(2, 2))

    assert board.get_atom(Hex(2, 2)) is a
    assert a.connection_at(1) is b


def test_get_state_reflects_atoms():
    board = Board(2, 2)
    board.place_atom(Hex(0, 1), Atom(AtomType.BASIC))

    state = board.get_state()

    assert state.shape == (2, 2, 2)
    assert state[1, 0, 1] == AtomType.BASIC
    assert state[1, 0, 0] == AtomType.NONE
    assert np.all(state[0] == -1)  # empty base layer is ComponentType.EMPTY


def test_connect_atoms_bonds_adjacent_pair():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)
    board.place_atom(Hex(0, 1), b)

    assert board.connect_atoms(Hex(0, 0), Hex(0, 1)) is True

    rotation = Direction().rotation_between(Hex(0, 0), Hex(0, 1))
    assert a.connection_at(rotation) is b
    assert b.connection_at((rotation + 3) % 6) is a


def test_connect_atoms_requires_both_atoms():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)

    assert board.connect_atoms(Hex(0, 0), Hex(0, 1)) is False  # dst empty
    assert board.connect_atoms(Hex(1, 0), Hex(0, 0)) is False  # src empty

    assert all(neighbor is None for neighbor in a.connections)


def test_connect_atoms_out_of_bounds():
    board = Board(3, 3)
    board.place_atom(Hex(0, 0), Atom(AtomType.BASIC))

    assert board.connect_atoms(Hex(0, 0), Hex(0, -1)) is False


def test_connect_atoms_non_adjacent():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)
    board.place_atom(Hex(2, 2), b)

    assert board.connect_atoms(Hex(0, 0), Hex(2, 2)) is False
    assert all(neighbor is None for neighbor in a.connections)
    assert all(neighbor is None for neighbor in b.connections)


def test_connect_atoms_conflicting_slot_is_noop():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    c = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)
    board.place_atom(Hex(0, 1), b)

    rotation = Direction().rotation_between(Hex(0, 0), Hex(0, 1))
    assert board.connect_atoms(Hex(0, 0), Hex(0, 1)) is True  # a bonded to b

    # Free a's side for a third atom while a's slot still points at b.
    assert board.move_atom(Hex(0, 1), Hex(1, 1)) is True
    board.place_atom(Hex(0, 1), c)

    assert board.connect_atoms(Hex(0, 0), Hex(0, 1)) is True  # no-op on occupied slot

    assert a.connection_at(rotation) is b
    assert b.connection_at((rotation + 3) % 6) is a
    assert c.connection_at((rotation + 3) % 6) is None


def test_disconnect_atoms_clears_bond():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)
    board.place_atom(Hex(0, 1), b)
    assert board.connect_atoms(Hex(0, 0), Hex(0, 1)) is True

    assert board.disconnect_atoms(Hex(0, 0), Hex(0, 1)) is True

    rotation = Direction().rotation_between(Hex(0, 0), Hex(0, 1))
    assert a.connection_at(rotation) is None
    assert b.connection_at((rotation + 3) % 6) is None


def test_disconnect_atoms_unbonded_or_missing_returns_false():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)
    board.place_atom(Hex(0, 1), b)

    assert board.disconnect_atoms(Hex(0, 0), Hex(0, 1)) is False  # unbonded pair
    assert board.disconnect_atoms(Hex(0, 0), Hex(1, 1)) is False  # dst empty


def test_place_component_cells_places_all_cells():
    board = Board(3, 3)

    assert board.place_component_cells([Hex(1, 1), Hex(2, 2)], ComponentType.ARM, 7) is True

    assert board.base_obj[Hex(1, 1)] == ComponentType.ARM
    assert board.base_obj[Hex(2, 2)] == ComponentType.ARM
    assert board.components_ids[Hex(1, 1)] == 7
    assert board.components_ids[Hex(2, 2)] == 7


def test_place_component_cells_atomic_on_failure():
    board = Board(3, 3)
    board.place_componet(Hex(1, 1), ComponentType.ARM)

    assert board.place_component_cells([Hex(1, 1), Hex(2, 2)], ComponentType.ARM, 5) is False

    # blocked origin means the whole placement is rejected, (2,2) untouched
    assert board.base_obj[Hex(2, 2)] == ComponentType.EMPTY
    assert board.components_ids[Hex(2, 2)] == -1


def test_remove_component_cells_clears_all_cells():
    board = Board(3, 3)
    board.place_component_cells([Hex(1, 1), Hex(2, 2)], ComponentType.ARM, 7)

    board.remove_component_cells([Hex(1, 1), Hex(2, 2)])

    assert board.base_obj[Hex(1, 1)] == ComponentType.EMPTY
    assert board.base_obj[Hex(2, 2)] == ComponentType.EMPTY
    assert board.components_ids[Hex(1, 1)] == -1
    assert board.components_ids[Hex(2, 2)] == -1


def test_get_molecule_returns_positions_and_leaves_board():
    board = Board(3, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 0), a)
    board.place_atom(Hex(0, 1), b)
    board.connect_atoms(Hex(0, 0), Hex(0, 1))

    molecule = board.get_molecule(Hex(0, 0))

    assert molecule == {Hex(0, 0): a, Hex(0, 1): b}
    assert board.get_atom(Hex(0, 0)) is a
    assert board.get_atom(Hex(0, 1)) is b


def test_get_molecule_empty_cell_returns_empty():
    board = Board(3, 3)

    assert board.get_molecule(Hex(0, 0)) == {}
