from __future__ import annotations

from random import Random

from .agents import AStarAgent, find_path_to_any
from .game import Position, WumpusGame


def generate_random_game(
    size: int = 20,
    seed: int | None = None,
    pit_probability: float = 0.08,
    max_attempts: int = 10_000,
    require_agent_success: bool = False,
) -> WumpusGame:
    if size < 4:
        raise ValueError("El tamano minimo recomendado es 4.")
    if not 0 <= pit_probability < 1:
        raise ValueError("pit_probability debe estar en [0, 1).")

    rng = Random(seed)
    base_seed = seed if seed is not None else rng.randrange(1_000_000_000)

    for attempt in range(max_attempts):
        attempt_seed = base_seed + attempt
        attempt_rng = Random(attempt_seed)
        game = _build_candidate(size, attempt_seed, attempt_rng, pit_probability)
        path = find_path_to_any(game.start, {game.gold}, game.safe_cells(), game.neighbors)
        if path and (not require_agent_success or _agent_can_solve(game)):
            return game

    raise RuntimeError("No se pudo generar un mapa solucionable con esos parametros.")


def _agent_can_solve(game: WumpusGame) -> bool:
    simulation = game.clone_for_run()
    result = AStarAgent(max_steps=1200).solve(simulation)
    return result.status.value == "won"


def _build_candidate(
    size: int,
    seed: int,
    rng: Random,
    pit_probability: float,
) -> WumpusGame:
    start: Position = (0, 0)
    protected = {start, (0, 1), (1, 0)}
    cells = [(row, col) for row in range(size) for col in range(size) if (row, col) not in protected]
    wumpus = rng.choice(cells)
    gold_options = [cell for cell in cells if cell != wumpus]
    gold = rng.choice(gold_options)

    pits: set[Position] = set()
    for cell in cells:
        if cell in {wumpus, gold}:
            continue
        roll = rng.random()
        if roll < pit_probability:
            pits.add(cell)

    return WumpusGame(
        size=size,
        start=start,
        player=start,
        wumpus=wumpus,
        gold=gold,
        pits=pits,
        arrows=1,
        seed=seed,
    )
