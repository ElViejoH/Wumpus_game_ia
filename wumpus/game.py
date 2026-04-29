from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from random import Random
from typing import Iterable

Position = tuple[int, int]


class Direction(str, Enum):
    UP = "U"
    DOWN = "D"
    LEFT = "L"
    RIGHT = "R"


class GameStatus(str, Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class Percepts:
    hedor: bool = False
    brisa: bool = False

    def as_list(self) -> list[str]:
        values: list[str] = []
        if self.hedor:
            values.append("hedor")
        if self.brisa:
            values.append("brisa")
        return values


@dataclass
class WumpusGame:
    size: int = 20
    start: Position = (0, 0)
    player: Position = (0, 0)
    wumpus: Position = (19, 19)
    gold: Position = (19, 18)
    pits: set[Position] = field(default_factory=set)
    arrows: int = 1
    wumpus_alive: bool = True
    seed: int | None = None
    status: GameStatus = GameStatus.PLAYING
    message: str = "Juego iniciado."

    def in_bounds(self, position: Position) -> bool:
        row, col = position
        return 0 <= row < self.size and 0 <= col < self.size

    def neighbors(self, position: Position) -> list[Position]:
        row, col = position
        candidates = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
        return [candidate for candidate in candidates if self.in_bounds(candidate)]

    def safe_cells(self) -> set[Position]:
        hazards = set(self.pits)
        if self.wumpus_alive:
            hazards.add(self.wumpus)
        return {
            (row, col)
            for row in range(self.size)
            for col in range(self.size)
            if (row, col) not in hazards
        }

    def percepts_at(self, position: Position) -> Percepts:
        adjacent = set(self.neighbors(position))
        return Percepts(
            hedor=self.wumpus_alive and self.wumpus in adjacent,
            brisa=bool(self.pits & adjacent),
        )

    def move(self, position: Position, rng: Random | None = None) -> GameStatus:
        if self.status is not GameStatus.PLAYING:
            return self.status
        if position not in self.neighbors(self.player):
            raise ValueError(f"No se puede mover de {self.player} a {position}; no son adyacentes.")

        self.player = position
        self._resolve_current_cell(rng or Random(self.seed))
        return self.status

    def shoot(self, direction: Direction) -> GameStatus:
        if self.status is not GameStatus.PLAYING:
            return self.status
        if self.arrows <= 0:
            self.status = GameStatus.LOST
            self.message = "No quedan flechas."
            return self.status

        self.arrows -= 1
        row_step, col_step = {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[direction]

        row, col = self.player
        while True:
            row += row_step
            col += col_step
            position = (row, col)
            if not self.in_bounds(position):
                self.status = GameStatus.LOST
                self.message = "La flecha fallo y salio de la cueva."
                return self.status
            if position == self.wumpus:
                self.wumpus_alive = False
                self.message = "La flecha golpeo al Wumpus. Ahora el agente debe encontrar el oro."
                return self.status

    def direction_to(self, target: Position) -> Direction:
        player_row, player_col = self.player
        target_row, target_col = target
        if player_row == target_row:
            return Direction.RIGHT if target_col > player_col else Direction.LEFT
        if player_col == target_col:
            return Direction.DOWN if target_row > player_row else Direction.UP
        raise ValueError(f"{target} no esta en linea recta desde {self.player}.")

    def direction_to_neighbor(self, target: Position) -> Direction:
        player_row, player_col = self.player
        target_row, target_col = target
        delta = (target_row - player_row, target_col - player_col)
        directions = {
            (-1, 0): Direction.UP,
            (1, 0): Direction.DOWN,
            (0, -1): Direction.LEFT,
            (0, 1): Direction.RIGHT,
        }
        if delta not in directions:
            raise ValueError(f"{target} no es una celda adyacente a {self.player}.")
        return directions[delta]

    def shooting_cells(self) -> set[Position]:
        cells: set[Position] = set()
        wumpus_row, wumpus_col = self.wumpus
        for index in range(self.size):
            if index != wumpus_col:
                cells.add((wumpus_row, index))
            if index != wumpus_row:
                cells.add((index, wumpus_col))
        return cells & self.safe_cells()

    def render(self, reveal: bool = False, path: Iterable[Position] | None = None) -> str:
        path_set = set(path or [])
        rows: list[str] = []
        for row in range(self.size):
            symbols: list[str] = []
            for col in range(self.size):
                position = (row, col)
                symbol = "."
                if position in path_set:
                    symbol = "*"
                if position == self.start:
                    symbol = "S"
                if position == self.player:
                    symbol = "A"
                if reveal:
                    if position == self.wumpus:
                        symbol = "W"
                    elif position == self.gold:
                        symbol = "G"
                    elif position in self.pits:
                        symbol = "P"
                    elif position in path_set:
                        symbol = "*"
                    if position == self.start:
                        symbol = "S"
                    if position == self.player:
                        symbol = "A"
                symbols.append(symbol)
            rows.append(" ".join(symbols))
        return "\n".join(rows)

    def clone_for_run(self) -> WumpusGame:
        return WumpusGame(
            size=self.size,
            start=self.start,
            player=self.start,
            wumpus=self.wumpus,
            gold=self.gold,
            pits=set(self.pits),
            arrows=self.arrows,
            wumpus_alive=self.wumpus_alive,
            seed=self.seed,
        )

    def _resolve_current_cell(self, rng: Random) -> None:
        if self.player == self.gold:
            self.status = GameStatus.WON
            self.message = "El agente encontro el oro. Ganaste."
        elif self.wumpus_alive and self.player == self.wumpus:
            self.status = GameStatus.LOST
            self.message = "El Wumpus devoro al jugador."
        elif self.player in self.pits:
            self.status = GameStatus.LOST
            self.message = "El jugador cayo en un pozo."
        else:
            percepts = self.percepts_at(self.player).as_list()
            self.message = "Percepciones: " + (", ".join(percepts) if percepts else "ninguna")
