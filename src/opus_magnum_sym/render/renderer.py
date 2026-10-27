from typing import cast

import pygame

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.components import Manipulator
from opus_magnum_sym.elements.components.base_component import ComponentType
from opus_magnum_sym.render.colors import (
    ATOM,
    ATOM_COLORS,
    BACKGROUND,
    BOND,
    CELL_BORDER,
    CELL_CURRENT,
    CELL_EMPTY,
    CELL_FILLED,
    CELL_TEXT,
    CONNECTION,
    CONNECTOR,
    DISCONNECTOR,
    DUPLICATION_GLYPH_EXEMPLAR,
    DUPLICATION_GLYPH_TRANSMUTER,
    ENTRANCE,
    EXIT,
    HAND,
    HAND_HOLDING,
    HEX_BORDER,
    HEX_EMPTY,
    MANIPULATOR,
    PROGRAM_BG,
    PROGRAM_LABEL,
    SALT_TRANSMUTER,
)
from opus_magnum_sym.render.geometry import hex_vertices
from opus_magnum_sym.render.layout import HexLayout
from opus_magnum_sym.simulation.simulator import Simulator

_ACTION_ABBR: dict[StepActionType, str] = {
    StepActionType.NONE: "",
    StepActionType.GRAB: "G",
    StepActionType.RELEASE: "R",
    StepActionType.ROTATE_CLW: "CW",
    StepActionType.ROTATE_CCLW: "CCW",
    StepActionType.ROTATE_MOLECULE_CLW: "MCW",
    StepActionType.ROTATE_MOLECULE_CCLW: "MCCW",
    StepActionType.EXTEND: "EX",
    StepActionType.RETRACT: "RT",
    StepActionType.MOVE_POS: "M+",
    StepActionType.MOVE_NEG: "M-",
}

_PROGRAM_MIN_STEPS = 12


class BoardRenderer:
    def __init__(self, simulator: Simulator, hex_size: int = 32):
        pygame.init()

        self.sim = simulator
        self.board = simulator.board

        self.layout: HexLayout = HexLayout(hex_size)
        self.hex_size = hex_size

        self.screen = pygame.display.set_mode((1200, 900))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("consolas", 12)
        if self.font is None:
            self.font = pygame.font.Font(None, 12)

        self.offset_x = 80
        self.offset_y = 80

    def draw(self):
        pygame.event.pump()
        self.screen.fill(BACKGROUND)

        try:
            self._draw_grid()
            self._draw_components()
            self._draw_connections()
            self._draw_atom_bonds()
            self._draw_objects()
            self._draw_manipulator_hands()
            self._draw_programs()
            self._draw_ui_overlay()
        except Exception as e:
            print(f"Render error: {e}")

        pygame.display.flip()

    # grid
    def _draw_grid(self):
        for r in range(self.board.rows):
            for s in range(self.board.cols):
                cx, cy = self.layout.hex_to_pixel(r, s)
                cx += self.offset_x
                cy += self.offset_y

                poly = hex_vertices(cx, cy, self.hex_size)

                pygame.draw.polygon(self.screen, HEX_EMPTY, poly)
                pygame.draw.polygon(self.screen, HEX_BORDER, poly, 2)

                self._draw_cell_labels(cx, cy, r, s)

    def _draw_cell_labels(self, cx: float, cy: float, r: int, s: int):
        pad = 3
        half_sqrt3 = self.layout.SQRT_3 / 2

        r_label = self.font.render(str(r), True, (160, 160, 160))
        s_label = self.font.render(str(s), True, (160, 160, 160))

        # r label next to left edge
        left_x = cx - half_sqrt3 * self.hex_size + pad + r_label.get_width() / 2
        left_y = cy - r_label.get_height() / 2
        self.screen.blit(r_label, (left_x - r_label.get_width() / 2, left_y))

        # s next to top left
        top_left_x = cx - half_sqrt3 * self.hex_size / 2 + 0.5 * pad
        top_left_y = cy - 0.75 * self.hex_size + pad + s_label.get_height() / 2
        self.screen.blit(
            s_label,
            (
                top_left_x - s_label.get_width() / 2,
                top_left_y - s_label.get_height() / 2,
            ),
        )

    # static components (arm bases, etc)
    def _draw_components(self):
        for r in range(self.board.rows):
            for s in range(self.board.cols):
                comp = int(self.board.base_obj[r, s])

                if comp == ComponentType.EMPTY:
                    continue

                cx, cy = self.layout.hex_to_pixel(r, s)
                cx += self.offset_x
                cy += self.offset_y

                if comp in (
                    ComponentType.ARM,
                    ComponentType.ARM_RETR,
                ):
                    inner_poly = hex_vertices(
                        cx,
                        cy,
                        self.hex_size * 0.45,
                    )

                    pygame.draw.polygon(
                        self.screen,
                        MANIPULATOR,
                        inner_poly,
                    )

                    pygame.draw.polygon(
                        self.screen,
                        (240, 200, 120),
                        inner_poly,
                        2,
                    )

                    pygame.draw.circle(
                        self.screen,
                        (80, 60, 40),
                        (cx, cy),
                        self.hex_size // 5,
                    )

                elif comp == ComponentType.ENTRANCE:
                    comp_id = int(self.board.components_ids[r, s])
                    comp_obj = self.sim.entrypoints.get(comp_id)
                    color = (
                        self._atom_type_color(comp_obj.atom_type)
                        if comp_obj is not None
                        else ENTRANCE
                    )
                    half = int(self.hex_size * 0.35)
                    rect = pygame.Rect(cx - half, cy - half, 2 * half, 2 * half)
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, (240, 255, 240), rect, 1)

                elif comp == ComponentType.EXIT:
                    comp_id = int(self.board.components_ids[r, s])
                    comp_obj = self.sim.entrypoints.get(comp_id)
                    color = (
                        self._atom_type_color(comp_obj.atom_type)
                        if comp_obj is not None
                        else EXIT
                    )
                    radius = int(self.hex_size * 0.47)
                    diamond = [
                        (cx, cy - radius),
                        (cx + radius, cy),
                        (cx, cy + radius),
                        (cx - radius, cy),
                    ]
                    pygame.draw.polygon(self.screen, color, diamond)
                    pygame.draw.polygon(self.screen, (255, 240, 240), diamond, 1)

                elif comp == ComponentType.CONNECTOR:
                    radius = int(self.hex_size * 0.3)
                    pygame.draw.circle(self.screen, CONNECTOR, (cx, cy), radius)
                    pygame.draw.circle(self.screen, (235, 240, 255), (cx, cy), radius, 1)

                elif comp == ComponentType.DISCONNECTOR:
                    radius = int(self.hex_size * 0.3)
                    pygame.draw.circle(self.screen, DISCONNECTOR, (cx, cy), radius, 1)
                    d = int(radius * 0.6)
                    pygame.draw.line(
                        self.screen,
                        DISCONNECTOR,
                        (cx - d, cy - d),
                        (cx + d, cy + d),
                        2,
                    )
                    pygame.draw.line(
                        self.screen,
                        DISCONNECTOR,
                        (cx - d, cy + d),
                        (cx + d, cy - d),
                        2,
                    )

                elif comp == ComponentType.SALT_TRANSMUTER:
                    radius = int(self.hex_size * 0.4)
                    triangle = [
                        (cx, cy - radius),
                        (cx + radius, cy + radius),
                        (cx - radius, cy + radius),
                    ]
                    pygame.draw.polygon(self.screen, SALT_TRANSMUTER, triangle)
                    pygame.draw.polygon(self.screen, (240, 220, 255), triangle, 1)

                elif comp == ComponentType.DUPLICATION_GLYPH:
                    self._draw_duplication_glyph(cx, cy, r, s)

    def _draw_duplication_glyph(self, cx: float, cy: float, r: int, s: int):
        comp_id = int(self.board.components_ids[r, s])
        comp_obj = self.sim.entrypoints.get(comp_id)
        is_transmuter = comp_obj is not None and (r, s) == (
            comp_obj.pos.r,
            comp_obj.pos.s,
        )
        radius = int(self.hex_size * 0.4)
        if is_transmuter:
            points = [
                (cx, cy - radius),
                (cx + radius, cy + radius),
                (cx - radius, cy + radius),
            ]
            color = DUPLICATION_GLYPH_TRANSMUTER
        else:
            points = [
                (cx, cy + radius),
                (cx + radius, cy - radius),
                (cx - radius, cy - radius),
            ]
            color = DUPLICATION_GLYPH_EXEMPLAR
        pygame.draw.polygon(self.screen, color, points)
        pygame.draw.polygon(self.screen, (240, 240, 240), points, 1)

    # link lines between connected entrances/exits
    def _draw_connections(self):
        entrypoints = self.sim.entrypoints
        drawn: set[tuple[int, ...]] = set()

        for cid, comp in entrypoints.items():
            ax, ay = self.layout.hex_to_pixel(comp.pos.r, comp.pos.s)
            ax += self.offset_x
            ay += self.offset_y

            for other_id in self.sim.connections.links_of(cid):
                other = entrypoints.get(other_id)
                if other is None:
                    continue

                key = tuple(sorted((cid, other_id)))
                if key in drawn:
                    continue
                drawn.add(key)

                bx, by = self.layout.hex_to_pixel(other.pos.r, other.pos.s)
                bx += self.offset_x
                by += self.offset_y

                pygame.draw.line(self.screen, CONNECTION, (ax, ay), (bx, by), 6)
                pygame.draw.line(self.screen, (40, 90, 40), (ax, ay), (bx, by), 2)

    # bond lines between connected atoms currently on board
    def _draw_atom_bonds(self):
        pos_of = {atom: cell for cell, atom in self.board.atoms.items()}
        drawn: set[frozenset[int]] = set()

        for cell, atom in self.board.atoms.items():
            ax, ay = self.layout.hex_to_pixel(cell.r, cell.s)
            ax += self.offset_x
            ay += self.offset_y

            for neighbor in atom.connections:
                if neighbor is None:
                    continue

                ncell = pos_of.get(neighbor)
                if ncell is None:
                    continue

                key = frozenset((id(atom), id(neighbor)))
                if key in drawn:
                    continue
                drawn.add(key)

                bx, by = self.layout.hex_to_pixel(ncell.r, ncell.s)
                bx += self.offset_x
                by += self.offset_y

                pygame.draw.line(self.screen, BOND, (ax, ay), (bx, by), 3)

    @staticmethod
    def _atom_color(atom: Atom) -> tuple[int, int, int]:
        return BoardRenderer._atom_type_color(atom.type)

    @staticmethod
    def _atom_type_color(atom_type: AtomType) -> tuple[int, int, int]:
        return ATOM_COLORS.get(atom_type.name, ATOM)

    # objects (atoms)
    def _draw_objects(self):
        for cell, atom in self.board.atoms.items():
            cx, cy = self.layout.hex_to_pixel(cell.r, cell.s)
            cx += self.offset_x
            cy += self.offset_y

            color = self._atom_color(atom)

            # outer glow
            pygame.draw.circle(
                self.screen,
                (220, 240, 255),
                (cx, cy),
                int(self.hex_size * 0.4),
            )

            # inner core
            pygame.draw.circle(
                self.screen,
                color,
                (cx, cy),
                int(self.hex_size * 0.3),
            )

            # atom highlight
            highlight_offset = max(2, self.hex_size // 12)
            pygame.draw.circle(
                self.screen,
                (255, 255, 255),
                (int(cx - highlight_offset), int(cy - highlight_offset)),
                max(2, self.hex_size // 16),
            )

    # manipulator
    def _draw_manipulator_hands(self):
        for comp in self.sim.components.values():
            if comp.type not in (
                ComponentType.ARM,
                ComponentType.ARM_RETR,
            ):
                continue

            comp = cast(Manipulator, comp)

            hand = comp.get_hand_pos

            hx, hy = self.layout.hex_to_pixel(hand.r, hand.s)
            hx += self.offset_x
            hy += self.offset_y

            bx, by = self.layout.hex_to_pixel(
                comp.pos.r,
                comp.pos.s,
            )

            bx += self.offset_x
            by += self.offset_y

            pygame.draw.line(
                self.screen,
                (220, 180, 90),
                (bx, by),
                (hx, hy),
                4,
            )

            pygame.draw.line(
                self.screen,
                (120, 90, 40),
                (bx, by),
                (hx, hy),
                1,
            )

            pygame.draw.circle(
                self.screen,
                HAND,
                (int(hx), int(hy)),
                self.hex_size // 4,
                3,
            )

            if comp.holding is not None:
                pygame.draw.circle(
                    self.screen,
                    HAND_HOLDING,
                    (int(hx), int(hy)),
                    self.hex_size // 7,
                )

                # mini held atom colored by the atom at the hand
                held_atom = comp.holding.get(comp.get_hand_pos)
                mini_color = self._atom_color(held_atom) if held_atom is not None else (255, 220, 220)
                pygame.draw.circle(
                    self.screen,
                    mini_color,
                    (int(hx), int(hy)),
                    self.hex_size // 10,
                )

    # per-component program bars pinned to the bottom of the window
    def _draw_programs(self):
        width, height = self.screen.get_size()
        components = {
            cid: comp
            for cid, comp in {**self.sim.entrypoints, **self.sim.components}.items()
            if comp.type
            not in (
                ComponentType.ENTRANCE,
                ComponentType.EXIT,
                ComponentType.CONNECTOR,
                ComponentType.DISCONNECTOR,
                ComponentType.SALT_TRANSMUTER,
                ComponentType.DUPLICATION_GLYPH,
            )
        }
        if not components:
            return

        ordered = sorted(components.values(), key=lambda comp: comp.idx)

        max_step = -1
        for comp in ordered:
            if comp._programm:
                max_step = max(max_step, *comp._programm)
        n_steps = max(_PROGRAM_MIN_STEPS, max_step + 1)

        margin = 10
        label_w = 132
        cell_h = 18
        row_h = cell_h + 6
        panel_h = margin + len(ordered) * row_h + margin
        panel_top = height - panel_h

        pygame.draw.rect(self.screen, PROGRAM_BG, (0, panel_top, width, panel_h))
        pygame.draw.line(
            self.screen,
            CELL_BORDER,
            (0, panel_top),
            (width, panel_top),
            2,
        )

        avail = width - label_w - 2 * margin
        cell_w = max(12.0, min(38.0, avail / n_steps))

        for i, comp in enumerate(ordered):
            y = panel_top + margin + i * row_h

            label = self.font.render(
                f"#{comp.idx} {comp.type.name.lower()}",
                True,
                PROGRAM_LABEL,
            )
            self.screen.blit(label, (margin, y + 2))

            for step in range(n_steps):
                x = label_w + margin + step * cell_w
                action = comp.get_step_action(step)
                filled = action != StepActionType.NONE

                cell = pygame.Rect(int(x), int(y), int(cell_w) - 2, cell_h)
                pygame.draw.rect(
                    self.screen,
                    CELL_FILLED if filled else CELL_EMPTY,
                    cell,
                )
                border = CELL_CURRENT if step == self.sim.step else CELL_BORDER
                pygame.draw.rect(self.screen, border, cell, 1)

                abbr = _ACTION_ABBR.get(action, "?")
                if abbr:
                    text = self.font.render(abbr, True, CELL_TEXT)
                    self.screen.blit(
                        text,
                        (
                            cell.centerx - text.get_width() // 2,
                            cell.centery - text.get_height() // 2,
                        ),
                    )

    def _draw_ui_overlay(self):
        text = self.font.render(
            f"step={self.sim.step}",
            True,
            (220, 220, 220),
        )
        self.screen.blit(text, (10, 10))

    def tick(self, fps: float = 60):
        self.clock.tick(fps)

    def process_events(self) -> bool:
        return all(event.type != pygame.QUIT for event in pygame.event.get())
