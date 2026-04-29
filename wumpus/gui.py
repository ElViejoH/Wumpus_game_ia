from __future__ import annotations

import tkinter as tk
import sys
from pathlib import Path
from random import Random
from tkinter import ttk

from PIL import Image, ImageTk

from .agents import AStarAgent, AgentStep, GreedyAgent, SolveResult
from .game import GameStatus, Percepts, Position, WumpusGame
from .generator import generate_random_game


BOARD_SIZE = 20
PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ASSET_DIR = PROJECT_ROOT / "assets"


COLORS = {
    "bg": "#e7eef7",
    "panel": "#f8fbff",
    "panel_strong": "#ffffff",
    "ink": "#0f172a",
    "muted": "#64748b",
    "line": "#cbd5e1",
    "primary": "#2563eb",
    "primary_dark": "#1d4ed8",
    "agent": "#2563eb",
    "gold": "#facc15",
    "wumpus": "#ef4444",
    "pit": "#111827",
    "breeze": "#bfdbfe",
    "stench": "#fed7aa",
    "both": "#fdba74",
    "visited": "#dbeafe",
    "safe": "#a7f3d0",
    "route": "#fde047",
    "suspect": "#fed7aa",
    "frontier": "#f1f5f9",
    "empty": "#f8fafc",
    "log_bg": "#0f172a",
    "log_fg": "#dbeafe",
}


class WumpusApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Hunt the Wumpus IA")
        self.geometry("1280x760")
        self.minsize(1160, 680)
        self.configure(bg=COLORS["bg"])

        self.random = Random()
        self.game: WumpusGame
        self.visited: set[Position] = set()
        self.discovered_percepts: dict[Position, Percepts] = {}
        self.agent_safe: set[Position] = set()
        self.agent_frontier: set[Position] = set()
        self.agent_possible_wumpus: set[Position] = set()
        self.agent_possible_pits: set[Position] = set()
        self.ai_path: list[Position] = []
        self.traveled_path: list[Position] = []
        self.ai_actions: list[str] = []
        self.agent_steps: list[AgentStep] = []
        self.pending_result: SolveResult | None = None
        self.is_running = False
        self.cell_size_by_canvas: dict[tk.Canvas, int] = {}
        self.board_offset_by_canvas: dict[tk.Canvas, tuple[int, int]] = {}
        self.raw_images: dict[str, Image.Image] = {}
        self.sprite_cache: dict[tuple[str, int], ImageTk.PhotoImage] = {}
        self.sprite_refs: list[ImageTk.PhotoImage] = []

        self.agent_var = tk.StringVar(value="astar")
        self.seed_var = tk.StringVar(value="--")
        self.status_var = tk.StringVar(value="Esperando")
        self.percepts_var = tk.StringVar(value="ninguna")
        self.steps_var = tk.StringVar(value="0")
        self.position_var = tk.StringVar(value="(0, 0)")
        self.action_var = tk.StringVar(value="Esperando inicio.")

        self._configure_style()
        self._load_assets()
        self._build_layout()
        self.new_seed()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=COLORS["panel_strong"], background=COLORS["panel_strong"])
        style.configure("TRadiobutton", background=COLORS["panel"], foreground=COLORS["ink"])

    def _load_assets(self) -> None:
        for name in ("agent", "gold", "pit", "wumpus"):
            path = ASSET_DIR / f"{name}.jpeg"
            if path.exists():
                self.raw_images[name] = Image.open(path).convert("RGB")

    def _build_layout(self) -> None:
        shell = tk.Frame(self, bg=COLORS["bg"])
        shell.pack(fill=tk.BOTH, expand=True, padx=22, pady=22)
        shell.grid_columnconfigure(0, weight=1, uniform="main")
        shell.grid_columnconfigure(1, weight=0, minsize=330)
        shell.grid_rowconfigure(0, weight=1)

        main_panel = tk.Frame(shell, bg=COLORS["bg"])
        main_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_columnconfigure(1, weight=1)
        main_panel.grid_rowconfigure(1, weight=1)

        title = tk.Frame(main_panel, bg=COLORS["bg"])
        title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        title.grid_columnconfigure(0, weight=1)
        self._label(title, "SIMULACION IA", 9, COLORS["muted"], bold=True).grid(row=0, column=0, sticky="w")
        self._label(title, "Hunt the Wumpus", 30, COLORS["ink"], bold=True).grid(row=1, column=0, sticky="w")
        self.status_pill = tk.Label(
            title,
            textvariable=self.status_var,
            bg=COLORS["panel_strong"],
            fg=COLORS["ink"],
            padx=14,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
        )
        self.status_pill.grid(row=0, column=1, rowspan=2, sticky="e")

        self.world_canvas = self._create_board_panel(
            main_panel,
            row=1,
            column=0,
            title="Mundo",
            subtitle="Mapa completo: oro, Wumpus, pozos, hedor y brisa.",
            badge="omnisciente",
        )
        self.agent_canvas = self._create_board_panel(
            main_panel,
            row=1,
            column=1,
            title="Agente",
            subtitle="Conocimiento parcial: visitadas, seguras y sospechas.",
            badge="percepcion",
        )

        legend = self._card(main_panel)
        legend.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        legend.grid_columnconfigure(tuple(range(8)), weight=1)
        for index, (text, color) in enumerate(
            [
                ("Agente", COLORS["agent"]),
                ("Oro", COLORS["gold"]),
                ("Wumpus", COLORS["wumpus"]),
                ("Pozo", COLORS["pit"]),
                ("Brisa", "#38bdf8"),
                ("Hedor", "#fb923c"),
                ("Seguro", COLORS["safe"]),
                ("Sospecha", COLORS["suspect"]),
            ]
        ):
            self._legend_item(legend, text, color).grid(row=0, column=index, sticky="w", padx=8, pady=8)

        sidebar = tk.Frame(shell, bg=COLORS["bg"])
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(3, weight=1)

        controls = self._card(sidebar)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        controls.grid_columnconfigure(0, weight=1)
        self._label(controls, "CONTROL", 9, COLORS["muted"], bold=True).grid(row=0, column=0, sticky="w")
        self._label(controls, "Exploracion automatica", 15, COLORS["ink"], bold=True).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 12)
        )
        button_row = tk.Frame(controls, bg=COLORS["panel"])
        button_row.grid(row=2, column=0, sticky="ew")
        button_row.grid_columnconfigure(0, weight=1)
        button_row.grid_columnconfigure(1, weight=1)
        self.new_button = self._button(button_row, "Nuevo juego", self.new_seed, primary=False)
        self.new_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.solve_button = self._button(button_row, "Iniciar", self.solve_with_ai, primary=True)
        self.solve_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._label(controls, "Algoritmo", 9, COLORS["muted"], bold=True).grid(row=3, column=0, sticky="w", pady=(14, 4))
        agent_select = ttk.Combobox(
            controls,
            textvariable=self.agent_var,
            values=("astar", "greedy"),
            state="readonly",
            font=("Segoe UI", 10),
        )
        agent_select.grid(row=4, column=0, sticky="ew")

        metrics = tk.Frame(sidebar, bg=COLORS["bg"])
        metrics.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        metrics.grid_columnconfigure(0, weight=1)
        metrics.grid_columnconfigure(1, weight=1)
        self._metric(metrics, "Semilla", self.seed_var).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        self._metric(metrics, "Pasos", self.steps_var).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))
        self._metric(metrics, "Posicion", self.position_var).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self._metric(metrics, "Percepcion", self.percepts_var).grid(row=1, column=1, sticky="ew", padx=(6, 0))

        action_card = self._card(sidebar)
        action_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self._label(action_card, "ACCION ACTUAL", 9, COLORS["muted"], bold=True).grid(row=0, column=0, sticky="w")
        self._label(action_card, "", 11, COLORS["ink"], textvariable=self.action_var, wraplength=280).grid(
            row=1, column=0, sticky="ew", pady=(6, 0)
        )

        log_card = self._card(sidebar)
        log_card.grid(row=3, column=0, sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(2, weight=1)
        header = tk.Frame(log_card, bg=COLORS["panel"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        self._label(header, "REGISTRO", 9, COLORS["muted"], bold=True).grid(row=0, column=0, sticky="w")
        self._button(header, "Limpiar", self._clear_log, primary=False).grid(row=0, column=1, sticky="e")
        self._label(log_card, "Eventos del agente", 15, COLORS["ink"], bold=True).grid(row=1, column=0, sticky="w", pady=(2, 8))
        self.log = tk.Text(
            log_card,
            bg=COLORS["log_bg"],
            fg=COLORS["log_fg"],
            insertbackground=COLORS["log_fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Cascadia Mono", 9),
            padx=10,
            pady=10,
            height=10,
        )
        self.log.grid(row=2, column=0, sticky="nsew")

    def _create_board_panel(self, parent: tk.Frame, row: int, column: int, title: str, subtitle: str, badge: str) -> tk.Canvas:
        card = self._card(parent)
        card.grid(row=row, column=column, sticky="nsew", padx=(0, 9) if column == 0 else (9, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        header = tk.Frame(card, bg=COLORS["panel"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)
        self._label(header, title, 15, COLORS["ink"], bold=True).grid(row=0, column=0, sticky="w")
        self._label(header, subtitle, 9, COLORS["muted"], wraplength=310).grid(row=1, column=0, sticky="w", pady=(2, 0))
        tk.Label(
            header,
            text=badge,
            bg=COLORS["panel_strong"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=5,
        ).grid(row=0, column=1, sticky="ne")

        canvas = tk.Canvas(card, bg=COLORS["empty"], highlightthickness=1, highlightbackground=COLORS["line"])
        canvas.grid(row=1, column=0, sticky="nsew")
        canvas.bind("<Configure>", lambda _event: self.draw_boards())
        return canvas

    def _card(self, parent: tk.Misc) -> tk.Frame:
        frame = tk.Frame(parent, bg=COLORS["panel"], padx=14, pady=14, highlightthickness=1, highlightbackground=COLORS["line"])
        return frame

    def _label(
        self,
        parent: tk.Misc,
        text: str,
        size: int,
        color: str,
        bold: bool = False,
        textvariable: tk.StringVar | None = None,
        wraplength: int | None = None,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            textvariable=textvariable,
            bg=parent["bg"] if isinstance(parent, tk.Widget) else COLORS["panel"],
            fg=color,
            font=("Segoe UI", size, "bold" if bold else "normal"),
            justify=tk.LEFT,
            wraplength=wraplength or 0,
        )

    def _button(self, parent: tk.Misc, text: str, command: object, primary: bool) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=COLORS["primary"] if primary else COLORS["panel_strong"],
            fg="#ffffff" if primary else COLORS["ink"],
            activebackground=COLORS["primary_dark"] if primary else "#eef2ff",
            activeforeground="#ffffff" if primary else COLORS["ink"],
            relief=tk.FLAT,
            padx=12,
            pady=9,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )

    def _metric(self, parent: tk.Misc, title: str, value: tk.StringVar) -> tk.Frame:
        frame = self._card(parent)
        self._label(frame, title.upper(), 8, COLORS["muted"], bold=True).grid(row=0, column=0, sticky="w")
        self._label(frame, "", 14, COLORS["ink"], bold=True, textvariable=value).grid(row=1, column=0, sticky="w", pady=(4, 0))
        return frame

    def _legend_item(self, parent: tk.Misc, text: str, color: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=COLORS["panel"])
        swatch = tk.Canvas(frame, width=12, height=12, bg=COLORS["panel"], highlightthickness=0)
        swatch.create_rectangle(1, 1, 11, 11, fill=color, outline=COLORS["line"])
        swatch.grid(row=0, column=0, padx=(0, 5))
        self._label(frame, text, 9, COLORS["ink"], bold=True).grid(row=0, column=1)
        return frame

    def new_seed(self) -> None:
        if self.is_running:
            return
        seed = self.random.randrange(1, 1_000_000)
        self.seed_var.set(str(seed))
        self.game = generate_random_game(
            size=BOARD_SIZE,
            seed=seed,
            pit_probability=0.04,
            require_agent_success=True,
        )
        self.visited = {self.game.start}
        self.discovered_percepts = {self.game.start: self.game.percepts_at(self.game.start)}
        self.agent_safe = {self.game.start}
        self.agent_frontier = set(self.game.neighbors(self.game.start))
        self.agent_possible_wumpus = set()
        self.agent_possible_pits = set()
        self.ai_path = []
        self.traveled_path = [self.game.start]
        self.ai_actions = []
        self.agent_steps = []
        self.pending_result = None
        self._clear_log()
        self.steps_var.set("0")
        self.action_var.set("Esperando inicio.")
        self._log(f"Nuevo juego generado con semilla {self.game.seed}.")
        self._update_status()
        self.draw_boards()

    def solve_with_ai(self) -> None:
        if self.is_running:
            return
        agent = AStarAgent() if self.agent_var.get() == "astar" else GreedyAgent()
        simulation = self.game.clone_for_run()
        result = agent.solve(simulation)
        self.pending_result = result
        self.agent_steps = list(agent.steps)
        self.ai_path = result.path
        self.traveled_path = []
        self.ai_actions = result.actions
        self._log(f"IA seleccionada: {agent.name}")
        self._log("Objetivo: encontrar el oro usando solo percepciones y memoria.")
        if not self.agent_steps:
            self._log(result.message)
            self.draw_boards()
            return
        self.is_running = True
        self.solve_button.configure(state=tk.DISABLED)
        self.new_button.configure(state=tk.DISABLED)
        self.steps_var.set("0")
        self.action_var.set("Iniciando recorrido.")
        self._animate_ai(index=0)

    def _animate_ai(self, index: int) -> None:
        if index < len(self.agent_steps):
            step = self.agent_steps[index]
            self.game.player = step.position
            self.visited.add(self.game.player)
            if not self.traveled_path or self.traveled_path[-1] != self.game.player:
                self.traveled_path.append(self.game.player)

            self.discovered_percepts[self.game.player] = step.percepts
            self.agent_safe = set(step.safe)
            self.agent_frontier = set(step.frontier)
            self.agent_possible_wumpus = set(step.possible_wumpus)
            self.agent_possible_pits = set(step.possible_pits)

            move_count = max(len(self.traveled_path) - 1, 0)
            self.steps_var.set(str(move_count))
            self.action_var.set(f"{step.action}: {step.message}")
            self._log(f"{index:03d} | {step.action:<8} | {step.position} | {step.message}")
            self._update_status()
            self.draw_boards()
            self.after(35, lambda: self._animate_ai(index + 1))
            return

        if self.pending_result is not None:
            self.game.status = self.pending_result.status
            self.game.message = self.pending_result.message

        self.is_running = False
        self.solve_button.configure(state=tk.NORMAL)
        self.new_button.configure(state=tk.NORMAL)
        self.steps_var.set(str(max(len(self.traveled_path) - 1, 0)))
        self.action_var.set(self.game.message)
        self._log(self.game.message)
        self._update_status()
        self.draw_boards()

    def draw_boards(self) -> None:
        if not hasattr(self, "game"):
            return
        self.sprite_refs = []
        self._draw_world_board()
        self._draw_agent_board()

    def _draw_world_board(self) -> None:
        self.world_canvas.delete("all")
        path_set = set(self.traveled_path)
        for row in range(self.game.size):
            for col in range(self.game.size):
                position = (row, col)
                fill = self._world_cell_color(position, path_set)
                self._draw_cell(self.world_canvas, position, fill, self._world_label(position))

    def _draw_agent_board(self) -> None:
        self.agent_canvas.delete("all")
        path_set = set(self.traveled_path)
        for row in range(self.game.size):
            for col in range(self.game.size):
                position = (row, col)
                fill = self._agent_cell_color(position, path_set)
                label = self._agent_label(position)
                self._draw_cell(self.agent_canvas, position, fill, label)

    def _board_geometry(self, canvas: tk.Canvas) -> tuple[int, int, int]:
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        board_px = min(width, height)
        cell_size = max(board_px // BOARD_SIZE, 1)
        board_px = cell_size * BOARD_SIZE
        offset_x = (width - board_px) // 2
        offset_y = (height - board_px) // 2
        self.cell_size_by_canvas[canvas] = cell_size
        self.board_offset_by_canvas[canvas] = (offset_x, offset_y)
        return cell_size, offset_x, offset_y

    def _draw_cell(self, canvas: tk.Canvas, position: Position, fill: str, label: str) -> None:
        row, col = position
        cell_size, offset_x, offset_y = self._board_geometry(canvas)
        x0 = offset_x + col * cell_size
        y0 = offset_y + row * cell_size
        x1 = x0 + cell_size
        y1 = y0 + cell_size
        canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=COLORS["line"], width=1)
        sprite = self._sprite_for_position(position, canvas)
        if sprite is not None:
            margin = max(cell_size * 0.08, 1)
            canvas.create_image(x0 + margin, y0 + margin, image=sprite, anchor=tk.NW)
            self.sprite_refs.append(sprite)
        if label and cell_size >= 14:
            canvas.create_text(
                x0 + cell_size / 2,
                y0 + cell_size / 2,
                text=label,
                fill=self._label_color(label),
                font=("Cascadia Mono", max(7, cell_size // 4), "bold"),
            )

    def _sprite_for_position(self, position: Position, canvas: tk.Canvas) -> ImageTk.PhotoImage | None:
        cell_size = self.cell_size_by_canvas.get(canvas, 1)
        sprite_size = max(int(cell_size * 0.84), 1)
        name: str | None = None
        if position == self.game.player:
            name = "agent"
        elif canvas is self.world_canvas and position == self.game.gold:
            name = "gold"
        elif canvas is self.world_canvas and self.game.wumpus_alive and position == self.game.wumpus:
            name = "wumpus"
        elif canvas is self.world_canvas and position in self.game.pits:
            name = "pit"
        if name is None or name not in self.raw_images:
            return None
        cache_key = (name, sprite_size)
        if cache_key not in self.sprite_cache:
            image = self.raw_images[name].resize((sprite_size, sprite_size), Image.Resampling.LANCZOS)
            self.sprite_cache[cache_key] = ImageTk.PhotoImage(image)
        return self.sprite_cache[cache_key]

    def _world_cell_color(self, position: Position, path_set: set[Position]) -> str:
        if position == self.game.player:
            return COLORS["agent"]
        if position == self.game.gold:
            return COLORS["gold"]
        if self.game.wumpus_alive and position == self.game.wumpus:
            return COLORS["wumpus"]
        if position in self.game.pits:
            return COLORS["pit"]
        percepts = self.game.percepts_at(position)
        if percepts.hedor and percepts.brisa:
            return COLORS["both"]
        if percepts.hedor:
            return COLORS["stench"]
        if percepts.brisa:
            return COLORS["breeze"]
        if position in path_set:
            return COLORS["route"]
        if position in self.visited:
            return COLORS["visited"]
        return COLORS["empty"]

    def _agent_cell_color(self, position: Position, path_set: set[Position]) -> str:
        if position == self.game.player:
            return COLORS["agent"]
        if position in path_set and position in self.visited:
            return COLORS["route"]
        if position in self.visited:
            return COLORS["visited"]
        if position in self.agent_safe:
            return COLORS["safe"]
        if position in self.agent_possible_wumpus or position in self.agent_possible_pits:
            return COLORS["suspect"]
        if position in self.agent_frontier:
            return COLORS["frontier"]
        return "#ffffff"

    def _world_label(self, position: Position) -> str:
        if position == self.game.player:
            return "A"
        if position == self.game.start:
            return "S"
        if position == self.game.gold:
            return "O"
        if self.game.wumpus_alive and position == self.game.wumpus:
            return "W"
        if position in self.game.pits:
            return "P"
        percepts = self.game.percepts_at(position)
        labels: list[str] = []
        if percepts.hedor:
            labels.append("He")
        if percepts.brisa:
            labels.append("Br")
        return "+".join(labels)

    def _agent_label(self, position: Position) -> str:
        if position == self.game.player:
            return "A"
        if position == self.game.start:
            return "S"
        if position not in self.visited:
            guesses: list[str] = []
            if position in self.agent_possible_wumpus:
                guesses.append("W?")
            if position in self.agent_possible_pits:
                guesses.append("P?")
            return "/".join(guesses)
        percepts = self.discovered_percepts.get(position)
        if not percepts:
            return ""
        labels: list[str] = []
        if percepts.hedor:
            labels.append("He")
        if percepts.brisa:
            labels.append("Br")
        return "+".join(labels)

    def _label_color(self, label: str) -> str:
        if label in {"A", "W", "P"}:
            return "#ffffff"
        if label == "O":
            return "#713f12"
        if label in {"He", "Br"} or "+" in label:
            return "#7c2d12"
        if "?" in label:
            return "#9a3412"
        return COLORS["ink"]

    def _update_status(self) -> None:
        status = self.game.status.value
        self.status_var.set("Explorando" if status == "playing" else "Victoria" if status == "won" else "Perdida")
        self.position_var.set(str(self.game.player))
        percepts = self.game.percepts_at(self.game.player).as_list()
        self.percepts_var.set(", ".join(percepts) if percepts else "ninguna")

    def _log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def _clear_log(self) -> None:
        self.log.delete("1.0", tk.END)


def run_gui() -> None:
    app = WumpusApp()
    app.mainloop()
