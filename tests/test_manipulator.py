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

    assert arm.holding is atom
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

    assert arm.holding is atom
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

    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 2), blocker)

    arm.assign_step_action(1, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    arm.execute_step(board, 1)

    arm.assign_step_action(2, StepActionType.RELEASE)
    arm.execute_step(board, 2)

    assert arm.holding is atom
    assert board.get_atom(Hex(1, 2)) is blocker
