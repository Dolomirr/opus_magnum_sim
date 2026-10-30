"""
Hardcoded costs for the built-in high-level components.

Costs are keyed by blueprint name.
Per-level entrypoint shapes are not listed and therefore cost 0.
"""

# TODO: tune these costs
COMPONENT_COSTS: dict[str, int] = {
    "arm": 10,
    "arm_piston": 20,
    "connector_straight_2": 10,
    "connector_tri": 30,
    "connector_tri_odd": 30,
    "salt_transmuter": 10,
    "glyph_duplication": 20,
}


def component_cost(name: str) -> int:
    """
    Cost of a placed blueprint by name; unknown names (entrypoint shapes) cost 0.
    """
    return COMPONENT_COSTS.get(name, 0)
