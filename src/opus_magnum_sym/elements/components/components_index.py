from opus_magnum_sym.elements.components import ComponentType, Connector, Disconnector, Enter, Exit
from opus_magnum_sym.elements.components.base_component import Component, ComponentAssignmentError
from opus_magnum_sym.elements.components.manipulator import Manipulator, RetractableManipulator

_COMPONENT_MAP: dict[ComponentType, type[Component]] = {
    ComponentType.ARM: Manipulator,
    ComponentType.ARM_RETR: RetractableManipulator,
    ComponentType.ENTRANCE: Enter,
    ComponentType.EXIT: Exit,
    ComponentType.CONNECTOR: Connector,
    ComponentType.DISCONNECTOR: Disconnector,
}


# TODO: move that loginc to base component type
def get_component_type(comp_type: ComponentType) -> type[Component]:
    """
    Provides generator for `Component` subclass by `ComponentType` enum.

    Usage:
    get_component_type(ComponentType.ARM)(args*, **kwargs)
    """
    if (cls := _COMPONENT_MAP.get(comp_type)) is None:
        msg = "Unknown component."
        raise ComponentAssignmentError(msg, comp_type)
    return cls
