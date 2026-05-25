from typing import cast

import pygame

from opus_magnum_sym.elements.components import Manipulator
from opus_magnum_sym.elements.components.base_component import ComponentType
from opus_magnum_sym.elements.objects.base_object import ObjectType
from opus_magnum_sym.render.colors import (
    ATOM,
    BACKGROUND,
    ENTRANCE,
    EXIT,
    HAND,
    HAND_HOLDING,
    HEX_BORDER,
    HEX_EMPTY,
    MANIPULATOR,
)
from opus_magnum_sym.render.geometry import hex_vertices
from opus_magnum_sym.render.layout import HexLayout
from opus_magnum_sym.simulation.simulator import Simulator


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

        self.offset_x = 80
        self.offset_y = 80

    def draw(self):
        self.screen.fill(BACKGROUND)

        self._draw_grid()
        self._draw_components()
        self._draw_objects()
        self._draw_manipulator_hands()
        self._draw_ui_overlay()

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
                comp = self.board.base_obj[r, s]

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
        for r in range(self.board.rows):
            for s in range(self.board.cols):
                obj = self.board.objects[r, s]

                if obj == ObjectType.NONE:
                    continue

                cx, cy = self.layout.hex_to_pixel(r, s)
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

            if comp.holding != ObjectType.NONE:
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
