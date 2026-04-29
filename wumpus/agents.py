from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import count
from random import Random
from typing import Callable, Iterable

from .game import Direction, GameStatus, Percepts, Position, WumpusGame


@dataclass
class SolveResult:
    status: GameStatus
    message: str
    path: list[Position]
    actions: list[str]


@dataclass
class AgentStep:
    position: Position
    action: str
    message: str
    percepts: Percepts
    safe: set[Position] = field(default_factory=set)
    visited: set[Position] = field(default_factory=set)
    frontier: set[Position] = field(default_factory=set)
    possible_wumpus: set[Position] = field(default_factory=set)
    possible_pits: set[Position] = field(default_factory=set)


@dataclass
class AgentKnowledge:
    size: int
    visited: set[Position] = field(default_factory=set)
    safe: set[Position] = field(default_factory=set)
    not_wumpus: set[Position] = field(default_factory=set)
    not_pit: set[Position] = field(default_factory=set)
    possible_wumpus: set[Position] = field(default_factory=set)
    possible_pits: set[Position] = field(default_factory=set)
    percepts: dict[Position, Percepts] = field(default_factory=dict)
    wumpus_candidates: list[set[Position]] = field(default_factory=list)

    def all_cells(self) -> set[Position]:
        return {(row, col) for row in range(self.size) for col in range(self.size)}

    def neighbors(self, position: Position) -> list[Position]:
        row, col = position
        candidates = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
        return [(r, c) for r, c in candidates if 0 <= r < self.size and 0 <= c < self.size]

    def frontier(self) -> set[Position]:
        cells: set[Position] = set()
        for cell in self.visited:
            cells.update(self.neighbors(cell))
        return cells - self.visited

    def observe(self, position: Position, percepts: Percepts) -> None:
        self.visited.add(position)
        self.safe.add(position)
        self.not_wumpus.add(position)
        self.not_pit.add(position)
        self.percepts[position] = percepts

        adjacent = set(self.neighbors(position)) - self.visited

        if percepts.hedor:
            self.wumpus_candidates.append(adjacent)
        else:
            self.not_wumpus.update(adjacent)

        if not percepts.brisa:
            self.not_pit.update(adjacent)

        self._refresh_possible_wumpus()
        self._refresh_possible_hazards()
        self._refresh_safety()

    def _refresh_possible_wumpus(self) -> None:
        if not self.wumpus_candidates:
            self.possible_wumpus = set()
            return

        groups = [group - self.not_wumpus - self.visited for group in self.wumpus_candidates if group]
        candidates = set.union(*groups) if groups else set()
        self.possible_wumpus = candidates - self.not_wumpus - self.visited

    def _refresh_possible_hazards(self) -> None:
        pit_groups = [
            set(self.neighbors(position)) - self.not_pit - self.visited
            for position, percepts in self.percepts.items()
            if percepts.brisa
        ]
        self.possible_pits = (set.union(*pit_groups) if pit_groups else set()) - self.not_pit - self.visited

    def _refresh_safety(self) -> None:
        self.possible_pits -= self.not_pit | self.visited
        hazard_suspects = self.possible_wumpus | self.possible_pits

        for cell in self.frontier():
            if cell not in hazard_suspects and cell in self.not_wumpus and cell in self.not_pit:
                self.safe.add(cell)

    def exact_wumpus(self) -> Position | None:
        candidates = self.possible_wumpus - self.visited
        if len(candidates) == 1:
            return next(iter(candidates))
        return None

    def least_risky_frontier(self) -> Position | None:
        frontier = self.frontier()
        if not frontier:
            return None
        return min(frontier, key=lambda cell: (self.risk(cell), cell[0], cell[1]))

    def risk(self, cell: Position) -> int:
        risk = 0
        if cell in self.possible_wumpus:
            risk += 4
        if cell in self.possible_pits:
            risk += 3
        if cell not in self.not_wumpus:
            risk += 1
        if cell not in self.not_pit:
            risk += 1
        return risk


NeighborFn = Callable[[Position], list[Position]]


def manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path_to_any(
    start: Position,
    goals: Iterable[Position],
    walkable: set[Position],
    neighbors: NeighborFn,
) -> list[Position]:
    goal_set = set(goals)
    if start in goal_set:
        return [start]
    if start not in walkable:
        return []

    tie_breaker = count()
    frontier: list[tuple[int, int, Position]] = []
    heappush(frontier, (0, next(tie_breaker), start))
    came_from: dict[Position, Position | None] = {start: None}

    while frontier:
        _, _, current = heappop(frontier)
        if current in goal_set:
            return reconstruct_path(came_from, current)
        for neighbor in neighbors(current):
            if neighbor not in walkable or neighbor in came_from:
                continue
            came_from[neighbor] = current
            heappush(frontier, (0, next(tie_breaker), neighbor))
    return []


def reconstruct_path(came_from: dict[Position, Position | None], current: Position) -> list[Position]:
    path = [current]
    while came_from[current] is not None:
        current = came_from[current]  # type: ignore[assignment]
        path.append(current)
    path.reverse()
    return path


class OnlineWumpusAgent:
    name = "A* exploratorio"

    def __init__(self, greedy: bool = False, max_steps: int = 1200) -> None:
        self.greedy = greedy
        self.max_steps = max_steps
        self.knowledge: AgentKnowledge | None = None
        self.steps: list[AgentStep] = []

    def solve(self, game: WumpusGame) -> SolveResult:
        rng = Random(game.seed)
        self.knowledge = AgentKnowledge(size=game.size)
        self.steps = []
        actions: list[str] = []
        path: list[Position] = [game.player]

        for step_index in range(self.max_steps):
            percepts = game.percepts_at(game.player)
            self.knowledge.observe(game.player, percepts)
            self._record(game.player, "analizar", f"Analiza percepciones en {game.player}.", percepts)

            wumpus = self.knowledge.exact_wumpus()
            if wumpus is not None:
                if game.player[0] == wumpus[0] or game.player[1] == wumpus[1]:
                    direction = game.direction_to(wumpus)
                    actions.append(f"disparar {direction.value} desde {game.player}")
                    game.shoot(direction)
                    self.knowledge.safe.add(wumpus)
                    self.knowledge.not_wumpus.add(wumpus)
                    self.knowledge.possible_wumpus.discard(wumpus)
                    self._record(game.player, f"disparar {direction.value}", game.message, percepts)

            target = self._choose_target(game.player)
            if target is None:
                message = "La IA no encontro una celda segura o razonable para seguir explorando."
                self._record(game.player, "detener", message, percepts)
                return SolveResult(GameStatus.LOST, message, path, actions)

            route = self._path_to(game.player, target)
            if len(route) < 2:
                message = "La IA no pudo construir una ruta con su conocimiento actual."
                self._record(game.player, "detener", message, percepts)
                return SolveResult(GameStatus.LOST, message, path, actions)

            next_cell = route[1]
            actions.append(f"mover {game.player} -> {next_cell}")
            previous = game.player
            game.move(next_cell, rng)
            path.append(game.player)
            self._record(game.player, f"mover {previous} -> {game.player}", game.message, game.percepts_at(game.player))

            if game.status is not GameStatus.PLAYING:
                return SolveResult(game.status, game.message, path, actions)

        message = f"La IA alcanzo el limite de {self.max_steps} pasos sin resolver."
        return SolveResult(GameStatus.LOST, message, path, actions)

    def _choose_target(self, current: Position) -> Position | None:
        assert self.knowledge is not None
        safe_frontier = (self.knowledge.safe & self.knowledge.frontier()) - {current}
        reachable_safe = {cell for cell in safe_frontier if self._path_to(current, cell)}
        if reachable_safe:
            return self._best_by_strategy(current, reachable_safe)

        risky_frontier = self.knowledge.frontier() - {current}
        reachable_risky = {cell for cell in risky_frontier if self._path_to(current, cell)}
        if not reachable_risky:
            return None
        return min(reachable_risky, key=lambda cell: (self.knowledge.risk(cell), manhattan(current, cell), cell[0], cell[1]))

    def _best_by_strategy(self, current: Position, targets: set[Position]) -> Position:
        assert self.knowledge is not None
        if self.greedy:
            return min(targets, key=lambda cell: (manhattan(current, cell), cell[0], cell[1]))
        return min(targets, key=lambda cell: (len(self._search(current, {cell}, self.knowledge.safe)) or 9999, cell[0], cell[1]))

    def _path_to(self, current: Position, target: Position) -> list[Position]:
        assert self.knowledge is not None
        walkable = set(self.knowledge.safe)
        walkable.add(target)
        return self._search(current, {target}, walkable)

    def _search(self, start: Position, goals: set[Position], walkable: set[Position]) -> list[Position]:
        assert self.knowledge is not None
        if self.greedy:
            return _greedy_search(start, goals, walkable, self.knowledge.neighbors)
        return _astar_search(start, goals, walkable, self.knowledge.neighbors)

    def _record(self, position: Position, action: str, message: str, percepts: Percepts) -> None:
        assert self.knowledge is not None
        self.steps.append(
            AgentStep(
                position=position,
                action=action,
                message=message,
                percepts=percepts,
                safe=set(self.knowledge.safe),
                visited=set(self.knowledge.visited),
                frontier=set(self.knowledge.frontier()),
                possible_wumpus=set(self.knowledge.possible_wumpus),
                possible_pits=set(self.knowledge.possible_pits),
            )
        )


class AStarAgent(OnlineWumpusAgent):
    name = "A* exploratorio"

    def __init__(self, max_steps: int = 1200) -> None:
        super().__init__(greedy=False, max_steps=max_steps)


class GreedyAgent(OnlineWumpusAgent):
    name = "Voraz exploratorio"

    def __init__(self, max_steps: int = 1200) -> None:
        super().__init__(greedy=True, max_steps=max_steps)


def _astar_search(start: Position, goals: set[Position], walkable: set[Position], neighbors: NeighborFn) -> list[Position]:
    if start in goals:
        return [start]
    if start not in walkable:
        return []

    tie_breaker = count()
    frontier: list[tuple[int, int, Position]] = []
    heappush(frontier, (0, next(tie_breaker), start))
    came_from: dict[Position, Position | None] = {start: None}
    cost_so_far: dict[Position, int] = {start: 0}

    while frontier:
        _, _, current = heappop(frontier)
        if current in goals:
            return reconstruct_path(came_from, current)
        for neighbor in neighbors(current):
            if neighbor not in walkable:
                continue
            new_cost = cost_so_far[current] + 1
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + min(manhattan(neighbor, goal) for goal in goals)
                came_from[neighbor] = current
                heappush(frontier, (priority, next(tie_breaker), neighbor))
    return []


def _greedy_search(start: Position, goals: set[Position], walkable: set[Position], neighbors: NeighborFn) -> list[Position]:
    if start in goals:
        return [start]
    if start not in walkable:
        return []

    tie_breaker = count()
    frontier: list[tuple[int, int, Position]] = []
    heappush(frontier, (0, next(tie_breaker), start))
    came_from: dict[Position, Position | None] = {start: None}

    while frontier:
        _, _, current = heappop(frontier)
        if current in goals:
            return reconstruct_path(came_from, current)
        for neighbor in neighbors(current):
            if neighbor not in walkable or neighbor in came_from:
                continue
            priority = min(manhattan(neighbor, goal) for goal in goals)
            came_from[neighbor] = current
            heappush(frontier, (priority, next(tie_breaker), neighbor))
    return []
