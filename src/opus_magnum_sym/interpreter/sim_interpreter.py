import shlex
from pathlib import Path

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.objects.base_object import ObjectType


class SimInterpreter:
    def __init__(self, sim):
        self.sim = sim

        # map string commands to handlers
        self.dispatch = {
            "comp": self._handle_comp,
            "c": self._handle_comp,
            "action": self._handle_action,
            "a": self._handle_action,
            "connection": self._handle_connection,
        }

    def load_file(self, filepath):
        with Path.open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                self.evaluate_line(line.strip(), line_num)

    def evaluate_line(self, line, line_num=0):
        # line comments
        if not line or line.startswith("#"):
            return

        tokens = shlex.split(line)
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
            if key == "object_type":
                kwargs[key] = getattr(ObjectType, value.upper())
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

    def _handle_connection(self, args):
        # TODO: not yet implemented
        pass
