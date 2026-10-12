import numpy as np
import pytest

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Board, Hex


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
