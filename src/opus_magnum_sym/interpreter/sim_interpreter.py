import shlex
from pathlib import Path

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType


class SimInterpreter:
    def __init__(self, sim):
        self.sim = sim

        # map string commands to handlers
        self.dispatch = {
            "comp": self._handle_comp,
            "c": self._handle_comp,
            "action": self._handle_action,
            "a": self._handle_action,
            "remove": self._handle_remove,
            "rm": self._handle_remove,
            "connection": self._handle_connection,
            "disconnection": self._handle_disconnection,
            "target": self._handle_target,
        }

    def load_file(self, filepath):
        with Path.open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                self.evaluate_line(line.strip(), line_num)

    def evaluate_line(self, line, line_num=0):
        # full-line and inline comments
        if not line or line.startswith("#"):
            return

        tokens = shlex.split(line, comments=True)
        if not tokens:
            return
        cmd = tokens[0].lower()

        if cmd in self.dispatch:
            try:
                self.dispatch[cmd](tokens[1:])
            except Exception as e:
                print(f"Error parsing line {line_num}: '{line}' -> {e}")
        else:
            print(f"Unknown command '{cmd}' on line {line_num}")

    def _handle_comp(self, args):
        # x, y, comp_type, [key=value ...]
        x, y = int(args[0]), int(args[1])
        comp_type = getattr(ComponentType, args[2].upper())

        kwargs = {}
        for arg in args[3:]:
            key, value = arg.split("=", 1)
            if key == "atom_type":
                kwargs[key] = getattr(AtomType, value.upper())
            elif key in ("rotation", "length"):
                kwargs[key] = int(value)
            else:
                kwargs[key] = value

        self.sim.add_component(
            cell=Hex(x, y),
            comp_type=comp_type,
            **kwargs,
        )

    def _handle_action(self, args):
        # comp_id, step, action_type
        comp_id = int(args[0])
        step = int(args[1])

        action_type_str = args[2].upper()
        action_type = getattr(StepActionType, action_type_str)

        self.sim.assign_step_action(
            comp_id=comp_id,
            step=step,
            action=action_type,
        )

    def _handle_remove(self, args):
        # comp_id
        comp_id = int(args[0])
        self.sim.remove_component(comp_id)

    def _handle_connection(self, args):
        # comp_id_a, comp_id_b
        id_a = int(args[0])
        id_b = int(args[1])
        if not self.sim.connect_components(id_a, id_b):
            print(f"Failed to connect components {id_a} and {id_b}")

    def _handle_disconnection(self, args):
        # comp_id_a, comp_id_b
        id_a = int(args[0])
        id_b = int(args[1])
        if not self.sim.disconnect_components(id_a, id_b):
            print(f"Failed to disconnect components {id_a} and {id_b}")

    def _handle_target(self, args):
        # count, exit_id [exit_id ...]
        if len(args) < 2:
            raise ValueError("target requires <count> <exit_id> [exit_id...]")
        count = int(args[0])
        exit_ids = [int(a) for a in args[1:]]
        self.sim.set_exit_target(exit_ids, count)
