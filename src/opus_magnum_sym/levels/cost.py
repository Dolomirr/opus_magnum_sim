"""
Hardcoded component costs used by the level solution metric.

Entrypoints and empty cells are do not have assigned cost.
"""

from opus_magnum_sym.elements.components import ComponentType

# TODO: add componed connectors
# TODO: tune these costs
COMPONENT_COSTS: dict[ComponentType, int] = {
    ComponentType.ARM: 10,
    ComponentType.ARM_RETR: 20,
    ComponentType.CONNECTOR: 10,
    ComponentType.DISCONNECTOR: 10,
    ComponentType.SALT_TRANSMUTER: 10,
    ComponentType.DUPLICATION_GLYPH: 20,
    ComponentType.TRANSPORTER: 10,
}


def component_cost(comp_type: ComponentType) -> int:
    """
    Cost of a component type; unmapped types (entrances, exits, empty) cost 0.
    """
    return COMPONENT_COSTS.get(comp_type, 0)
