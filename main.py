from __future__ import annotations

import argparse

from wumpus.agents import AStarAgent, GreedyAgent
from wumpus.generator import generate_random_game
from wumpus.gui import run_gui


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hunt the Wumpus 20x20 con IA.")
    parser.add_argument("--seed", type=int, default=None, help="Semilla para reproducir el mapa.")
    parser.add_argument("--size", type=int, default=20, help="Tamano de la grilla NxN.")
    parser.add_argument("--pit-probability", type=float, default=0.08, help="Probabilidad de pozo por celda.")
    parser.add_argument("--agent", choices=("astar", "greedy"), default="astar", help="Metodo de busqueda de la IA.")
    parser.add_argument("--show-board", action="store_true", help="Muestra el tablero con peligros.")
    parser.add_argument("--cli", action="store_true", help="Ejecuta la version de consola en lugar de la interfaz.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.cli:
        run_gui()
        return

    game = generate_random_game(
        size=args.size,
        seed=args.seed,
        pit_probability=args.pit_probability,
    )

    agent = AStarAgent() if args.agent == "astar" else GreedyAgent()
    result = agent.solve(game)

    print(f"Metodo: {agent.name}")
    print(f"Semilla: {game.seed}")
    print(f"Tamano: {game.size}x{game.size}")
    print(f"Inicio: {game.start}")
    print(f"Wumpus: {game.wumpus}")
    print(f"Oro: {game.gold}")
    print(f"Estado final: {result.status}")
    print(f"Mensaje: {result.message}")
    print(f"Pasos recorridos: {len(result.path) - 1}")
    print(f"Acciones ejecutadas: {len(result.actions)}")

    if result.path:
        print("Ruta recorrida por el agente:")
        print(" -> ".join(str(position) for position in result.path))

    if result.actions:
        print("Acciones:")
        for action in result.actions:
            print(f"- {action}")

    if args.show_board:
        print("\nTablero:")
        print(game.render(reveal=True, path=set(result.path)))


if __name__ == "__main__":
    main()
