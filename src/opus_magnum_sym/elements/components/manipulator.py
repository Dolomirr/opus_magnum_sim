from typing import TYPE_CHECKING

from icecream import ic

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.actions.base_action import ActionAssignmentError
from opus_magnum_sym.elements.atoms.atom import Atom
from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.board.hex import Hex
from opus_magnum_sym.elements.components.base_component import Component, ComponentAssignmentError, ComponentType
from opus_magnum_sym.elements.components.blueprints import ManipulatorSpec
from opus_magnum_sym.simulation.collision import CollisionCategory, CollisionEvent
from opus_magnum_sym.simulation.errors import SimulationCollisionError
from opus_magnum_sym.simulation.movement import Movement, MovementKind

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board


class Manipulator(Component):
    _component_type = ComponentType.ARM

    def __init__(
        self,
        idx: int,
        pos: Hex,
        rotation: int = 0,
        length: int = 1,
        spec: ManipulatorSpec | None = None,
    ) -> None:
        super().__init__(
            idx=idx,
            type=self._component_type,
            pos=pos,
            rotation=rotation,
        )
        if spec is None:
            spec = ManipulatorSpec(
                name="arm",
                arm_count=1,
                extendable=False,
                min_length=1,
                max_length=6,
            )
        if spec.arm_count != 1:
            msg = f"Manipulator does not support arm_count={spec.arm_count}; only single-arm behavior is implemented."
            raise ComponentAssignmentError(msg, ComponentType.ARM)
        if not spec.min_length <= length <= spec.max_length:
            msg = (
                f"length {length} out of bounds for spec {spec.name!r}: "
                f"require {spec.min_length} <= length <= {spec.max_length}"
            )
            raise ComponentAssignmentError(msg, ComponentType.ARM)
        self.spec = spec
        self.hand_length: int = length  # TODO: check correct length
        # absolute cells of the currently held molecule
        self.holding: dict[Hex, Atom] | None = None

    @property
    def get_hand_pos(self) -> Hex:
        return (
            Direction().from_rotation(self.rotation)
            .apply(self.pos, self.hand_length)
        )  # fmt: skip

    def _positions_free(self, board: Board, positions: dict[Hex, Atom]) -> bool:
        """
        True when every target cell is in bounds and unoccupied.

        Out-of-bounds targets are a silent no-op (returns False).
        Taken/occupied target (board atom or another arm's held cell)
        raises `ENDPOINT_OVERLAP` collision instead of silently refusing.
        """
        if not all(board.in_bounds(pos) for pos in positions):
            return False
        for pos in positions:
            if pos in board.atoms or pos in self._blocked_cells:
                self._report_endpoint_overlap(pos)
        return True

    def _report_endpoint_overlap(self, cell: Hex) -> None:
        raise SimulationCollisionError(
            CollisionEvent(
                category=CollisionCategory.ENDPOINT_OVERLAP,
                step=self._step,
                cell=cell,
                owner_ids=(self.idx,),
                progress=1.0,
            )
        )

    def _record_movement(
        self,
        kind: MovementKind,
        pivot: Hex,
        rotation: int,
        holding: dict[Hex, Atom],
    ) -> None:
        if self._movement_recorder is None:
            return
        self._movement_recorder.append(
            Movement(
                owner_id=self.idx,
                kind=kind,
                pivot=pivot,
                rotation_steps=rotation,
                atoms=list(holding.items()),
            )
        )

    def _held_by_other_arm(self) -> bool:
        """
        True when any atom of molecule held by this arm
        is also held by another arm.
        Moving a molecule shared between arms would tear it into two places.
        """
        held_by_other = any(atom.held_by - {self.idx} for atom in self.holding.values())  # ty:ignore
        return self.holding is not None and held_by_other

    def _rotate(self, rotation: int, board: Board) -> None:
        if self.holding:
            if self._held_by_other_arm():
                return
            new_holding = {pos.rotate_around(self.pos, rotation): atom for pos, atom in self.holding.items()}
            if not self._positions_free(board, new_holding):
                return
            self._record_movement(MovementKind.ARM_SWING, self.pos, rotation, self.holding)
            self.holding = new_holding
            for atom in self.holding.values():
                atom.rotate_connections(rotation)
        self.rotation = (self.rotation + rotation) % 6

    def _rotate_molecule(self, rotation: int, board: Board) -> None:
        if not self.holding:
            return
        if self._held_by_other_arm():
            return
        new_holding = {pos.rotate_around(self.get_hand_pos, rotation): atom for pos, atom in self.holding.items()}
        if not self._positions_free(board, new_holding):
            return
        self._record_movement(MovementKind.MOLECULE_PIVOT, self.get_hand_pos, rotation, self.holding)
        self.holding = new_holding
        for atom in self.holding.values():
            atom.rotate_connections(rotation)

    def _extend(self, board: Board) -> None:
        msg = "Assigned EXTEND action to component that does not support this action."
        raise ActionAssignmentError(msg, self.type, self.idx)

    def _retract(self, board: Board) -> None:
        msg = "Assigned RETRACT action to component that does not support this action."
        raise ActionAssignmentError(msg, self.type, self.idx)

    def _grab(self, board: Board) -> None:
        if self.holding is None:
            hand = self.get_hand_pos
            grabbed = board.pop_molecule(hand)
            if grabbed:
                for atom in grabbed.values():
                    atom.held_by.add(self.idx)
                self.holding = grabbed
                self.log_action("grabbed", f"{len(grabbed)} atom(s)", hand)

    def _release(self, board: Board) -> None:
        if self.holding is None:
            return
        if self._held_by_other_arm():
            return
        if not self._positions_free(board, self.holding):
            return
        hand = self.get_hand_pos
        for pos, atom in self.holding.items():
            atom.held_by.discard(self.idx)
            board.place_atom(pos, atom)
        self.log_action("released", f"{len(self.holding)} atom(s)", hand)
        self.holding = None

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        match action_type:
            case StepActionType.NONE:
                pass
            case StepActionType.ROTATE_CLW:
                self._rotate(1, board)
            case StepActionType.ROTATE_CCLW:
                self._rotate(-1, board)
            case StepActionType.ROTATE_MOLECULE_CLW:
                self._rotate_molecule(1, board)
            case StepActionType.ROTATE_MOLECULE_CCLW:
                self._rotate_molecule(-1, board)
            case StepActionType.EXTEND:
                self._extend(board)
            case StepActionType.RETRACT:
                self._retract(board)
            case StepActionType.GRAB:
                self._grab(board)
            case StepActionType.RELEASE:
                self._release(board)
                # TODO: add movement action
            case _:
                msg = f"Invalid action assigned to component of type manipulator: {action_type} {self.idx}"
                raise ActionAssignmentError(msg, self.type, self.idx)


class RetractableManipulator(Manipulator):
    """
    Manipulator with an extendable arm whose hand slides along its rotation axis.

    Length ranges over `spec.min_length .. spec.max_length`. Extend moves the
    hand (and any held molecule) one cell further from the base; retract moves
    it one cell closer. The base cell stays fixed.
    """

    _component_type = ComponentType.ARM_RETR

    def __init__(
        self,
        idx: int,
        pos: Hex,
        rotation: int = 0,
        length: int = 1,
        spec: ManipulatorSpec | None = None,
    ) -> None:
        if spec is None:
            spec = ManipulatorSpec(
                name="arm_piston",
                arm_count=1,
                extendable=True,
                min_length=1,
                max_length=3,
            )
        super().__init__(idx=idx, pos=pos, rotation=rotation, length=length, spec=spec)

    def _translate(self, delta: int, board: Board) -> None:
        new_length = self.hand_length + delta
        if not self.spec.min_length <= new_length <= self.spec.max_length:
            return
        direction = Direction().from_rotation(self.rotation)
        if self.holding:
            if self._held_by_other_arm():
                return
            new_holding = {direction.apply(pos, delta): atom for pos, atom in self.holding.items()}
            if not self._positions_free(board, new_holding):
                return
            self._record_slide(direction, delta, self.holding)
            self.holding = new_holding
        self.hand_length = new_length

    def _record_slide(self, direction, delta: int, holding: dict[Hex, Atom]) -> None:
        if self._movement_recorder is None:
            return
        dr, ds = direction.offset
        self._movement_recorder.append(
            Movement(
                owner_id=self.idx,
                kind=MovementKind.HAND_SLIDE,
                pivot=self.pos,
                rotation_steps=delta,
                atoms=list(holding.items()),
                slide_delta=Hex(dr * delta, ds * delta),
            )
        )

    def _extend(self, board: Board) -> None:
        self._translate(1, board)

    def _retract(self, board: Board) -> None:
        self._translate(-1, board)
