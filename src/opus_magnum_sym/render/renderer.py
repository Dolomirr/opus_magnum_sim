from typing import cast

import pygame

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.components import Manipulator
from opus_magnum_sym.elements.components.base_component import ComponentType
from opus_magnum_sym.render.colors import (
    ATOM,
    BACKGROUND,
    CELL_BORDER,
    CELL_CURRENT,
    CELL_EMPTY,
    CELL_FILLED,
    CELL_TEXT,
    ENTRANCE,
    EXIT,
    HAND,
    HAND_HOLDING,
    HEX_BORDER,
    HEX_EMPTY,
    MANIPULATOR,
    PROGRAM_BG,
    PROGRAM_LABEL,
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

                label = self.font.render(f"{r},{s}", True, (160, 160, 160))
                self.screen.blit(label, (cx - 10, cy - 8))

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
                    pygame.draw.circle(
                        self.screen,
                        ENTRANCE,
                        (cx, cy),
                        self.hex_size // 2,
                    )

                    pygame.draw.polygon(
                        self.screen,
                        (240, 255, 240),
                        [
                            (cx - 8, cy),
                            (cx + 6, cy - 8),
                            (cx + 6, cy + 8),
                        ],
                    )

                elif comp == ComponentType.EXIT:
                    pygame.draw.circle(
                        self.screen,
                        EXIT,
                        (cx, cy),
                        self.hex_size // 2,
                    )

                    pygame.draw.polygon(
                        self.screen,
                        (255, 240, 240),
                        [
                            (cx + 8, cy),
                            (cx - 6, cy - 8),
                            (cx - 6, cy + 8),
                        ],
                    )

    # objects (atoms)
    def _draw_objects(self):
        for cell in self.board.atoms:
            cx, cy = self.layout.hex_to_pixel(cell.r, cell.s)
            cx += self.offset_x
            cy += self.offset_y

            # outer glow
            pygame.draw.circle(
                self.screen,
                (220, 240, 255),
                (cx, cy),
                self.hex_size // 3,
            )

            # inner core
            pygame.draw.circle(
                self.screen,
                ATOM,
                (cx, cy),
                self.hex_size // 4,
            )

            # atom highlight
            pygame.draw.circle(
                self.screen,
                (255, 255, 255),
                (cx - 3, cy - 3),
                2,
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

                # mini held atom
                pygame.draw.circle(
                    self.screen,
                    (255, 220, 220),
                    (int(hx), int(hy)),
                    self.hex_size // 10,
                )

    # per-component program bars pinned to the bottom of the window
    def _draw_programs(self):
        width, height = self.screen.get_size()
        components = {**self.sim.entrypoints, **self.sim.components}
        if not components:
            return

        ordered = sorted(components.values(), key=lambda comp: comp.idx)

        max_step = -1
        for comp in ordered:
            if comp._programm:
                max_step = max(max_step, max(comp._programm))
        n_steps = max(_PROGRAM_MIN_STEPS, max_step + 1)

        margin = 10
        label_w = 132
        cell_h = 18
        row_h = cell_h + 6
        panel_h = margin + len(ordered) * row_h + margin
        panel_top = height - panel_h

        pygame.draw.rect(self.screen, PROGRAM_BG, (0, panel_top, width, panel_h))
        pygame.draw.line(self.screen, CELL_BORDER, (0, panel_top), (width, panel_top), 2)

        avail = width - label_w - 2 * margin
        cell_w = max(12.0, min(38.0, avail / n_steps))

        for i, comp in enumerate(ordered):
            y = panel_top + margin + i * row_h

            label = self.font.render(f"#{comp.idx} {comp.type.name.lower()}", True, PROGRAM_LABEL)
            self.screen.blit(label, (margin, y + 2))

            for step in range(n_steps):
                x = label_w + margin + step * cell_w
                action = comp.get_step_action(step)
                filled = action != StepActionType.NONE

                cell = pygame.Rect(int(x), int(y), int(cell_w) - 2, cell_h)
                pygame.draw.rect(self.screen, CELL_FILLED if filled else CELL_EMPTY, cell)
                border = CELL_CURRENT if step == self.sim.step else CELL_BORDER
                pygame.draw.rect(self.screen, border, cell, 1)

                abbr = _ACTION_ABBR.get(action, "?")
                if abbr:
                    text = self.font.render(abbr, True, CELL_TEXT)
                    self.screen.blit(
                        text,
                        (cell.centerx - text.get_width() // 2, cell.centery - text.get_height() // 2),
                    )

    def _draw_ui_overlay(self):
        text = self.font.render(
            f"step={self.sim.step}",
            True,
            (220, 220, 220),
        )
        self.screen.blit(text, (10, 10))

    def tick(self, fps=60):
        self.clock.tick(fps)

    def process_events(self) -> bool:
        return all(event.type != pygame.QUIT for event in pygame.event.get())
