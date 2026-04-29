const SIZE = 20;
const PIT_PROBABILITY = 0.04;
const MAX_STEPS = 1200;
const COLORS = {
  empty: "#f8fafc",
  agent: "#2563eb",
  gold: "#facc15",
  wumpus: "#ef4444",
  pit: "#111827",
  breeze: "#bfdbfe",
  stench: "#fed7aa",
  both: "#fdba74",
  visited: "#dbeafe",
  safe: "#a7f3d0",
  route: "#fde047",
  suspect: "#fed7aa",
  frontier: "#f1f5f9",
};
const ASSETS = {
  agent: "../assets/agent.jpeg",
  gold: "../assets/gold.jpeg",
  pit: "../assets/pit.jpeg",
  wumpus: "../assets/wumpus.jpeg",
};

const state = {
  game: null,
  solution: null,
  stepIndex: 0,
  running: false,
  traveled: [],
  visited: new Set(),
  discovered: new Map(),
  knowledge: emptyKnowledge(),
};

const els = {
  world: document.querySelector("#worldBoard"),
  agent: document.querySelector("#agentBoard"),
  status: document.querySelector("#statusPill"),
  seed: document.querySelector("#seedMetric"),
  steps: document.querySelector("#stepsMetric"),
  position: document.querySelector("#positionMetric"),
  percept: document.querySelector("#perceptMetric"),
  action: document.querySelector("#actionText"),
  log: document.querySelector("#eventLog"),
  newGame: document.querySelector("#newGameBtn"),
  start: document.querySelector("#startBtn"),
  clearLog: document.querySelector("#clearLogBtn"),
  agentSelect: document.querySelector("#agentSelect"),
};

function key(pos) {
  return `${pos.r},${pos.c}`;
}

function fromKey(value) {
  const [r, c] = value.split(",").map(Number);
  return { r, c };
}

function same(a, b) {
  return a.r === b.r && a.c === b.c;
}

function rng(seed) {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

function randomInt(rand, min, max) {
  return Math.floor(rand() * (max - min + 1)) + min;
}

function emptyKnowledge() {
  return {
    safe: new Set(),
    visited: new Set(),
    frontier: new Set(),
    possibleWumpus: new Set(),
    possiblePits: new Set(),
  };
}

function neighbors(pos) {
  return [
    { r: pos.r - 1, c: pos.c },
    { r: pos.r + 1, c: pos.c },
    { r: pos.r, c: pos.c - 1 },
    { r: pos.r, c: pos.c + 1 },
  ].filter((p) => p.r >= 0 && p.r < SIZE && p.c >= 0 && p.c < SIZE);
}

function generateGame(seed, requireWin = true) {
  for (let attempt = 0; attempt < 2500; attempt += 1) {
    const currentSeed = seed + attempt;
    const rand = rng(currentSeed);
    const protectedCells = new Set(["0,0", "0,1", "1,0"]);
    const cells = [];
    for (let r = 0; r < SIZE; r += 1) {
      for (let c = 0; c < SIZE; c += 1) {
        if (!protectedCells.has(`${r},${c}`)) cells.push({ r, c });
      }
    }

    const wumpus = cells[randomInt(rand, 0, cells.length - 1)];
    let gold = cells[randomInt(rand, 0, cells.length - 1)];
    while (same(gold, wumpus)) gold = cells[randomInt(rand, 0, cells.length - 1)];

    const pits = new Set();
    for (const cell of cells) {
      if (same(cell, wumpus) || same(cell, gold)) continue;
      if (rand() < PIT_PROBABILITY) pits.add(key(cell));
    }

    const game = {
      seed: currentSeed,
      start: { r: 0, c: 0 },
      player: { r: 0, c: 0 },
      wumpus,
      gold,
      pits,
      arrows: 1,
      wumpusAlive: true,
      status: "playing",
      message: "Juego iniciado.",
    };

    if (!requireWin) return game;
    const result = solveGame(cloneGame(game), "astar");
    if (result.status === "won") return game;
  }
  throw new Error("No se pudo generar una partida apta para la demo.");
}

function cloneGame(game) {
  return {
    ...game,
    player: { ...game.start },
    pits: new Set(game.pits),
    wumpusAlive: true,
    status: "playing",
    message: "Juego iniciado.",
  };
}

function perceptsAt(game, pos) {
  const around = neighbors(pos);
  return {
    hedor: game.wumpusAlive && around.some((p) => same(p, game.wumpus)),
    brisa: around.some((p) => game.pits.has(key(p))),
  };
}

function perceptText(percepts) {
  const values = [];
  if (percepts.hedor) values.push("hedor");
  if (percepts.brisa) values.push("brisa");
  return values.length ? values.join(", ") : "ninguna";
}

function move(game, target) {
  game.player = { ...target };
  if (same(game.player, game.gold)) {
    game.status = "won";
    game.message = "El agente encontro el oro.";
  } else if (game.wumpusAlive && same(game.player, game.wumpus)) {
    game.status = "lost";
    game.message = "El Wumpus devoro al agente.";
  } else if (game.pits.has(key(game.player))) {
    game.status = "lost";
    game.message = "El agente cayo en un pozo.";
  } else {
    game.message = `Percepciones: ${perceptText(perceptsAt(game, game.player))}`;
  }
}

function shoot(game, target) {
  if (game.arrows <= 0) return;
  game.arrows -= 1;
  if (same(target, game.wumpus)) {
    game.wumpusAlive = false;
    game.message = "La flecha mato al Wumpus. El objetivo sigue siendo el oro.";
  }
}

function observe(knowledge, pos, percepts) {
  const posKey = key(pos);
  knowledge.visited.add(posKey);
  knowledge.safe.add(posKey);

  const adjacent = neighbors(pos).map(key).filter((k) => !knowledge.visited.has(k));
  if (percepts.hedor) {
    adjacent.forEach((k) => knowledge.possibleWumpus.add(k));
  } else {
    adjacent.forEach((k) => knowledge.possibleWumpus.delete(k));
  }

  if (percepts.brisa) {
    adjacent.forEach((k) => knowledge.possiblePits.add(k));
  } else {
    adjacent.forEach((k) => knowledge.possiblePits.delete(k));
  }

  knowledge.possibleWumpus.forEach((k) => {
    if (knowledge.visited.has(k)) knowledge.possibleWumpus.delete(k);
  });
  knowledge.possiblePits.forEach((k) => {
    if (knowledge.visited.has(k)) knowledge.possiblePits.delete(k);
  });

  knowledge.frontier = new Set();
  knowledge.visited.forEach((k) => neighbors(fromKey(k)).forEach((n) => {
    const nk = key(n);
    if (!knowledge.visited.has(nk)) knowledge.frontier.add(nk);
  }));

  knowledge.frontier.forEach((k) => {
    if (!knowledge.possibleWumpus.has(k) && !knowledge.possiblePits.has(k)) {
      knowledge.safe.add(k);
    }
  });
}

function solveGame(game, mode) {
  const knowledge = emptyKnowledge();
  const path = [key(game.player)];
  const steps = [];
  const actions = [];

  for (let i = 0; i < MAX_STEPS; i += 1) {
    const percepts = perceptsAt(game, game.player);
    observe(knowledge, game.player, percepts);
    steps.push(snapshot(game, knowledge, "analizar", `Percibe ${perceptText(percepts)}.`));

    const exactWumpus = knowledge.possibleWumpus.size === 1 ? fromKey([...knowledge.possibleWumpus][0]) : null;
    if (exactWumpus && (exactWumpus.r === game.player.r || exactWumpus.c === game.player.c)) {
      shoot(game, exactWumpus);
      knowledge.possibleWumpus.delete(key(exactWumpus));
      knowledge.safe.add(key(exactWumpus));
      steps.push(snapshot(game, knowledge, "disparar", game.message));
    }

    const target = chooseTarget(game.player, knowledge, mode);
    if (!target) {
      return { status: "lost", message: "El agente no encontro una ruta razonable.", path, steps, actions };
    }

    const route = search(game.player, target, new Set([...knowledge.safe, key(target)]), mode);
    if (route.length < 2) {
      return { status: "lost", message: "No hay ruta con el conocimiento actual.", path, steps, actions };
    }

    const next = fromKey(route[1]);
    actions.push(`mover ${key(game.player)} -> ${key(next)}`);
    move(game, next);
    path.push(key(game.player));
    steps.push(snapshot(game, knowledge, "mover", game.message));

    if (game.status !== "playing") {
      return { status: game.status, message: game.message, path, steps, actions };
    }
  }

  return { status: "lost", message: "Limite de pasos alcanzado.", path, steps, actions };
}

function snapshot(game, knowledge, action, message) {
  return {
    position: key(game.player),
    wumpusAlive: game.wumpusAlive,
    status: game.status,
    action,
    message,
    percepts: perceptsAt(game, game.player),
    safe: new Set(knowledge.safe),
    visited: new Set(knowledge.visited),
    frontier: new Set(knowledge.frontier),
    possibleWumpus: new Set(knowledge.possibleWumpus),
    possiblePits: new Set(knowledge.possiblePits),
  };
}

function chooseTarget(current, knowledge, mode) {
  const currentKey = key(current);
  const safeFrontier = [...knowledge.frontier].filter((k) => knowledge.safe.has(k) && k !== currentKey);
  const reachableSafe = safeFrontier.filter((k) => search(current, fromKey(k), knowledge.safe, mode).length);
  if (reachableSafe.length) return bestTarget(current, reachableSafe, knowledge.safe, mode);

  const risky = [...knowledge.frontier].filter((k) => k !== currentKey);
  const reachableRisky = risky.filter((k) => search(current, fromKey(k), new Set([...knowledge.safe, k]), mode).length);
  if (!reachableRisky.length) return null;
  reachableRisky.sort((a, b) => risk(a, knowledge) - risk(b, knowledge) || distance(current, fromKey(a)) - distance(current, fromKey(b)));
  return fromKey(reachableRisky[0]);
}

function bestTarget(current, keys, safe, mode) {
  keys.sort((a, b) => {
    if (mode === "greedy") return distance(current, fromKey(a)) - distance(current, fromKey(b));
    return search(current, fromKey(a), safe, mode).length - search(current, fromKey(b), safe, mode).length;
  });
  return fromKey(keys[0]);
}

function risk(cellKey, knowledge) {
  let score = 0;
  if (knowledge.possibleWumpus.has(cellKey)) score += 4;
  if (knowledge.possiblePits.has(cellKey)) score += 3;
  return score;
}

function distance(a, b) {
  return Math.abs(a.r - b.r) + Math.abs(a.c - b.c);
}

function search(start, target, walkable, mode) {
  const startKey = key(start);
  const targetKey = key(target);
  if (startKey === targetKey) return [startKey];
  if (!walkable.has(startKey)) return [];

  const frontier = [{ cell: startKey, priority: 0 }];
  const came = new Map([[startKey, null]]);
  const cost = new Map([[startKey, 0]]);

  while (frontier.length) {
    frontier.sort((a, b) => a.priority - b.priority);
    const current = frontier.shift().cell;
    if (current === targetKey) return reconstruct(came, current);
    for (const n of neighbors(fromKey(current)).map(key)) {
      if (!walkable.has(n)) continue;
      const nextCost = cost.get(current) + 1;
      if (!cost.has(n) || nextCost < cost.get(n)) {
        cost.set(n, nextCost);
        came.set(n, current);
        const heuristic = distance(fromKey(n), target);
        frontier.push({ cell: n, priority: mode === "greedy" ? heuristic : nextCost + heuristic });
      }
    }
  }
  return [];
}

function reconstruct(came, current) {
  const path = [current];
  while (came.get(current)) {
    current = came.get(current);
    path.push(current);
  }
  return path.reverse();
}

function drawBoard(svg, type) {
  svg.innerHTML = "";
  const traveled = new Set(state.traveled);
  for (let r = 0; r < SIZE; r += 1) {
    for (let c = 0; c < SIZE; c += 1) {
      const pos = { r, c };
      const posKey = key(pos);
      const { fill, label, color, image } = type === "world" ? worldCell(pos, traveled) : agentCell(pos, traveled);
      const rect = svgEl("rect", { x: c, y: r, width: 1, height: 1, fill, class: "cell" });
      svg.append(rect);
      if (image) {
        svg.append(svgEl("image", {
          href: image,
          x: c + 0.08,
          y: r + 0.08,
          width: 0.84,
          height: 0.84,
          preserveAspectRatio: "xMidYMid slice",
          class: "cell-image",
        }));
      }
      if (label) {
        svg.append(svgEl("text", {
          x: c + 0.5,
          y: r + 0.56,
          fill: color,
          class: "cell-label",
        }, label));
      }
    }
  }
}

function worldCell(pos, traveled) {
  const game = state.game;
  const posKey = key(pos);
  if (same(pos, game.player)) return { fill: COLORS.agent, label: "", color: "#fff", image: ASSETS.agent };
  if (same(pos, game.gold)) return { fill: COLORS.gold, label: "", color: "#713f12", image: ASSETS.gold };
  if (game.wumpusAlive && same(pos, game.wumpus)) return { fill: COLORS.wumpus, label: "", color: "#fff", image: ASSETS.wumpus };
  if (game.pits.has(posKey)) return { fill: COLORS.pit, label: "", color: "#fff", image: ASSETS.pit };
  const p = perceptsAt(game, pos);
  if (p.hedor && p.brisa) return { fill: COLORS.both, label: "He+Br", color: "#7c2d12" };
  if (p.hedor) return { fill: COLORS.stench, label: "He", color: "#7c2d12" };
  if (p.brisa) return { fill: COLORS.breeze, label: "Br", color: "#075985" };
  if (traveled.has(posKey)) return { fill: COLORS.route, label: "", color: "#000" };
  return { fill: COLORS.empty, label: "", color: "#000" };
}

function agentCell(pos, traveled) {
  const posKey = key(pos);
  const k = state.knowledge;
  if (same(pos, state.game.player)) return { fill: COLORS.agent, label: "", color: "#fff", image: ASSETS.agent };
  if (traveled.has(posKey)) return { fill: COLORS.route, label: agentKnownLabel(posKey), color: "#713f12" };
  if (k.visited.has(posKey)) return { fill: COLORS.visited, label: agentKnownLabel(posKey), color: "#1e3a8a" };
  if (k.safe.has(posKey)) return { fill: COLORS.safe, label: "", color: "#166534" };
  if (k.possibleWumpus.has(posKey) || k.possiblePits.has(posKey)) {
    const label = [k.possibleWumpus.has(posKey) ? "W?" : "", k.possiblePits.has(posKey) ? "P?" : ""].filter(Boolean).join("/");
    return { fill: COLORS.suspect, label, color: "#9a3412" };
  }
  if (k.frontier.has(posKey)) return { fill: COLORS.frontier, label: "", color: "#334155" };
  return { fill: "#fff", label: "", color: "#334155" };
}

function agentKnownLabel(posKey) {
  const p = state.discovered.get(posKey);
  if (!p) return "";
  const labels = [];
  if (p.hedor) labels.push("He");
  if (p.brisa) labels.push("Br");
  return labels.join("+");
}

function svgEl(name, attrs, text = "") {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  if (text) el.textContent = text;
  return el;
}

function newGame() {
  state.running = false;
  const seed = randomInt(Math.random, 1, 999999);
  state.game = generateGame(seed, true);
  resetViewKnowledge();
  log(`Nuevo juego generado con semilla ${state.game.seed}.`);
  render();
}

function resetViewKnowledge() {
  state.solution = null;
  state.stepIndex = 0;
  state.traveled = [key(state.game.start)];
  state.visited = new Set([key(state.game.start)]);
  state.discovered = new Map([[key(state.game.start), perceptsAt(state.game, state.game.start)]]);
  state.knowledge = emptyKnowledge();
  state.knowledge.safe.add(key(state.game.start));
  neighbors(state.game.start).forEach((n) => state.knowledge.frontier.add(key(n)));
  state.game.player = { ...state.game.start };
  state.game.status = "playing";
  state.game.message = "Juego iniciado.";
  els.log.textContent = "";
}

function start() {
  if (state.running) return;
  const simulation = cloneGame(state.game);
  state.solution = solveGame(simulation, els.agentSelect.value);
  state.stepIndex = 0;
  state.traveled = [];
  state.running = true;
  els.start.disabled = true;
  els.newGame.disabled = true;
  log(`IA ${els.agentSelect.value === "astar" ? "A*" : "Voraz"} iniciada. Objetivo: encontrar oro.`);
  tick();
}

function tick() {
  const step = state.solution.steps[state.stepIndex];
  if (!step) {
    state.running = false;
    state.game.status = state.solution.status;
    state.game.message = state.solution.message;
    els.start.disabled = false;
    els.newGame.disabled = false;
    log(state.solution.message);
    render();
    return;
  }

  const pos = fromKey(step.position);
  state.game.player = pos;
  state.game.wumpusAlive = step.wumpusAlive;
  state.game.status = step.status;
  state.visited.add(step.position);
  if (state.traveled.at(-1) !== step.position) state.traveled.push(step.position);
  state.discovered.set(step.position, step.percepts);
  state.knowledge = {
    safe: new Set(step.safe),
    visited: new Set(step.visited),
    frontier: new Set(step.frontier),
    possibleWumpus: new Set(step.possibleWumpus),
    possiblePits: new Set(step.possiblePits),
  };
  state.game.message = step.message;
  log(`${String(state.stepIndex).padStart(3, "0")} | ${step.action.padEnd(8, " ")} | ${step.position} | ${step.message}`);
  state.stepIndex += 1;
  render();
  window.setTimeout(tick, 35);
}

function render() {
  drawBoard(els.world, "world");
  drawBoard(els.agent, "agent");
  const p = perceptsAt(state.game, state.game.player);
  els.status.textContent = state.game.status === "playing" ? "Explorando" : state.game.status === "won" ? "Victoria" : "Perdida";
  els.seed.textContent = state.game.seed;
  els.steps.textContent = Math.max(0, state.traveled.length - 1);
  els.position.textContent = `(${state.game.player.r},${state.game.player.c})`;
  els.percept.textContent = perceptText(p);
  els.action.textContent = state.game.message;
}

function log(message) {
  els.log.textContent += `${message}\n`;
  els.log.scrollTop = els.log.scrollHeight;
}

els.newGame.addEventListener("click", newGame);
els.start.addEventListener("click", start);
els.clearLog.addEventListener("click", () => {
  els.log.textContent = "";
});

newGame();
