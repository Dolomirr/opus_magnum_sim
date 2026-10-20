import pytest  # noqa: INP001

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Board, Hex
from opus_magnum_sym.elements.components import Manipulator


def _arm_before_atom():
    """Arm at (1,1) rotation 0 (hand -> (0,2)) with an atom placed at the hand."""
    board = Board(5, 5)
    arm = Manipulator(idx=0, pos=Hex(1, 1), rotation=0)
    atom = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 2), atom)
    return board, arm, atom


def test_grab_picks_up_atom_from_hand_cell():
    board, arm, atom = _arm_before_atom()

    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    assert arm.holding == {Hex(0, 2): atom}
    assert board.get_atom(Hex(0, 2)) is None


def test_grab_on_empty_cell_is_noop():
    board = Board(5, 5)
    arm = Manipulator(idx=0, pos=Hex(1, 1), rotation=0)

    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    assert arm.holding is None


def test_grab_while_holding_is_noop():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    other = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 2), other)

    arm.assign_step_action(1, StepActionType.GRAB)
    arm.execute_step(board, 1)

    assert arm.holding == {Hex(0, 2): atom}
    assert board.get_atom(Hex(0, 2)) is other


def test_release_places_atom_and_clears_hand():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    arm.execute_step(board, 1)

    arm.assign_step_action(2, StepActionType.RELEASE)
    arm.execute_step(board, 2)

    assert arm.holding is None
    assert board.get_atom(Hex(1, 2)) is atom


def test_release_onto_occupied_cell_keeps_holding():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    arm.execute_step(board, 1)

    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 2), blocker)

    arm.assign_step_action(2, StepActionType.RELEASE)
    arm.execute_step(board, 2)

    assert arm.holding == {Hex(1, 2): atom}
    assert board.get_atom(Hex(1, 2)) is blocker


def test_rotate_into_occupied_cell_is_blocked():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 2), blocker)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2), occupied
    arm.execute_step(board, 1)

    assert arm.rotation == 0
    assert arm.holding == {Hex(0, 2): atom}
    assert board.get_atom(Hex(1, 2)) is blocker


def _arm_before_molecule():
    """Arm at (1,1) rotation 0 (hand -> (0,2)) with a bonded pair at (0,2)-(0,3)."""
    board = Board(5, 5)
    arm = Manipulator(idx=0, pos=Hex(1, 1), rotation=0)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(0, 2), a)
    board.place_atom(Hex(0, 3), b)
    board.connect_atoms(Hex(0, 2), Hex(0, 3))
    return board, arm, a, b


def test_grab_collects_whole_molecule():
    board, arm, a, b = _arm_before_molecule()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    assert arm.holding == {Hex(0, 2): a, Hex(0, 3): b}
    assert board.get_atom(Hex(0, 2)) is None
    assert board.get_atom(Hex(0, 3)) is None
    assert a.connection_at(1) is b
    assert b.connection_at(4) is a


def test_rotate_moves_held_molecule():
    board, arm, a, b = _arm_before_molecule()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)
    arm.execute_step(board, 1)

    assert arm.holding == {Hex(1, 2): a, Hex(2, 2): b}
    assert a.connection_at(2) is b
    assert b.connection_at(5) is a


def test_rotate_molecule_around_hand_keeps_arm_orientation():
    board, arm, a, b = _arm_before_molecule()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.ROTATE_MOLECULE_CLW)
    arm.execute_step(board, 1)

    assert arm.rotation == 0
    assert arm.holding == {Hex(0, 2): a, Hex(1, 2): b}
    assert a.connection_at(2) is b
    assert b.connection_at(5) is a


def test_rotate_molecule_into_occupied_cell_is_blocked():
    board, arm, a, b = _arm_before_molecule()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 2), blocker)  # b would land here on ROTATE_MOLECULE_CLW

    arm.assign_step_action(1, StepActionType.ROTATE_MOLECULE_CLW)
    arm.execute_step(board, 1)

    assert arm.holding == {Hex(0, 2): a, Hex(0, 3): b}
    assert a.connection_at(1) is b
    assert b.connection_at(4) is a
    assert board.get_atom(Hex(1, 2)) is blocker


def test_rotate_molecule_ccw_around_hand():
    board = Board(6, 6)
    arm = Manipulator(idx=0, pos=Hex(2, 2), rotation=0)  # hand -> (1, 3)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 3), a)
    board.place_atom(Hex(1, 4), b)
    board.connect_atoms(Hex(1, 3), Hex(1, 4))
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.ROTATE_MOLECULE_CCLW)
    arm.execute_step(board, 1)

    assert arm.rotation == 0
    assert arm.holding == {Hex(1, 3): a, Hex(0, 4): b}
    assert a.connection_at(0) is b
    assert b.connection_at(3) is a


def test_rotate_molecule_without_holding_is_noop():
    board = Board(5, 5)
    arm = Manipulator(idx=0, pos=Hex(1, 1), rotation=0)

    arm.assign_step_action(0, StepActionType.ROTATE_MOLECULE_CLW)
    arm.execute_step(board, 0)

    assert arm.rotation == 0
    assert arm.holding is None


def test_release_places_whole_molecule():
    board, arm, a, b = _arm_before_molecule()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)
    arm.assign_step_action(1, StepActionType.ROTATE_CLW)
    arm.execute_step(board, 1)

    arm.assign_step_action(2, StepActionType.RELEASE)
    arm.execute_step(board, 2)

    assert arm.holding is None
    assert board.get_atom(Hex(1, 2)) is a
    assert board.get_atom(Hex(2, 2)) is b
    assert a.connection_at(2) is b
    assert b.connection_at(5) is a


def test_release_blocked_keeps_whole_molecule():
    board, arm, a, b = _arm_before_molecule()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)
    arm.assign_step_action(1, StepActionType.ROTATE_CLW)
    arm.execute_step(board, 1)

    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(2, 2), blocker)

    arm.assign_step_action(2, StepActionType.RELEASE)
    arm.execute_step(board, 2)

    assert arm.holding == {Hex(1, 2): a, Hex(2, 2): b}
    assert board.get_atom(Hex(1, 2)) is None
    assert board.get_atom(Hex(2, 2)) is blocker


def test_grab_marks_atoms_held_by():
    board, arm, atom = _arm_before_atom()

    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    assert atom.held_by == {arm.idx}


def test_release_clears_held_by():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)
    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    arm.execute_step(board, 1)

    arm.assign_step_action(2, StepActionType.RELEASE)
    arm.execute_step(board, 2)

    assert atom.held_by == set()
    assert board.get_atom(Hex(1, 2)) is atom


def test_rotate_blocked_by_other_held_cell():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    arm.execute_step(board, 1, blocked_cells={Hex(1, 2)})

    assert arm.rotation == 0
    assert arm.holding == {Hex(0, 2): atom}


def test_release_blocked_by_other_held_cell():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    arm.assign_step_action(1, StepActionType.RELEASE)
    arm.execute_step(board, 1, blocked_cells={Hex(0, 2)})

    assert arm.holding == {Hex(0, 2): atom}
    assert atom.held_by == {arm.idx}
    assert board.get_atom(Hex(0, 2)) is None


def test_rotate_blocked_when_molecule_held_by_another_arm():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    # Simulate a second arm also holding this molecule.
    atom.held_by.add(999)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    arm.execute_step(board, 1)

    assert arm.rotation == 0
    assert arm.holding == {Hex(0, 2): atom}


def test_release_blocked_when_molecule_held_by_another_arm():
    board, arm, atom = _arm_before_atom()
    arm.assign_step_action(0, StepActionType.GRAB)
    arm.execute_step(board, 0)

    atom.held_by.add(999)

    arm.assign_step_action(1, StepActionType.RELEASE)
    arm.execute_step(board, 1)

    assert arm.holding == {Hex(0, 2): atom}
    assert board.get_atom(Hex(0, 2)) is None
