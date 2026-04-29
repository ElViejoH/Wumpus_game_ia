# Hunt the Wumpus IA - Contexto del proyecto

## Descripción general

Proyecto en Python para generar mapas aleatorios de **Hunt the Wumpus** en una grilla de `20x20` y resolverlos con agentes inteligentes que operan con información parcial.

El sistema incluye:
- Generador de mundo aleatorio y validación de soluciones.
- Lógica de juego con Wumpus, oro, pozos y percepciones.
- IA de exploración basada en A* y búsqueda voraz.
- Interfaz web responsiva con visualización del mundo completo y el conocimiento del agente.
- Interfaz Python/Tkinter para escritorio.

## Estructura del proyecto

### Archivos raíz

- `main.py`
  - CLI principal.
  - Permite ejecutar la aplicación en modo GUI o consola.
  - Parámetros: `--seed`, `--size`, `--pit-probability`, `--agent` (`astar` o `greedy`), `--show-board`, `--cli`.
  - Genera un juego con `wumpus.generator.generate_random_game` y resuelve con `AStarAgent` o `GreedyAgent`.

- `README.md`
  - Explica el propósito del proyecto, uso de las versiones web, GUI y CLI, y la arquitectura general.

- `HuntTheWumpusIA.spec`
  - Archivo de configuración para empaquetado, presumiblemente con PyInstaller.

### Carpeta `wumpus/`

- `wumpus/game.py`
  - Define el modelo del juego: `WumpusGame`, `Percepts`, `Direction`, `GameStatus`.
  - Implementa movimiento del agente, disparo de flecha, perceptos y renderizado del tablero.
  - Controla condiciones de victoria y derrota.

- `wumpus/generator.py`
  - Genera partidas aleatorias reproducibles.
  - Protege celdas iniciales y garantiza mapas resolvibles si se solicita.

- `wumpus/agents.py`
  - Gestiona el conocimiento del agente y la lógica de decisión.
  - Presenta `AgentKnowledge` y `OnlineWumpusAgent`.
  - Incorpora:
    - observación de perceptos,
    - inferencia de posibles Wumpus y pozos,
    - selección de objetivos seguros o de menor riesgo,
    - búsqueda de ruta con A* o modo voraz.

- `wumpus/gui.py`
  - Implementa la interfaz de escritorio con Tkinter.
  - Muestra el tablero completo, el tablero conocido por el agente, métricas y registros.

### Carpeta `web/`

- `web/index.html`
  - Interfaz principal de la simulación.
  - Dos tableros SVG: "Mundo" y "Agente".
  - Controles: nuevo juego, iniciar y selección de algoritmo.
  - Panel de métricas y log de eventos.

- `web/app.js`
  - Lógica de simulación dentro del navegador.
  - Genera el juego, controla el movimiento y observa perceptos.
  - Mantiene conocimiento parcial similar al agente Python.
  - Define celdas `safe`, `visited`, `frontier`, `possibleWumpus` y `possiblePits`.
  - Implementa resolución por exploración A* o voraz.

- `web/styles.css`
  - Estilos responsivos con CSS Grid y componentes de dashboard.
  - Diseño moderno para visualización clara de tableros y métricas.

## Comportamiento de la IA

- El agente no conoce el mapa completo.
- Decide con base en:
  - perceptos locales (`hedor`, `brisa`),
  - celdas visitadas,
  - celdas seguras,
  - posibles posiciones del Wumpus y de los pozos.
- Puede disparar la flecha si infiere la posición exacta del Wumpus.
- El objetivo final es encontrar el oro; matar al Wumpus es una acción complementaria.
- Hay dos estrategias principales:
  - exploración basada en A* (`astar`),
  - búsqueda voraz o greedy (`greedy`).

## Uso principal

### Web

- Abrir `web/index.html` en un navegador.

### Python / GUI

- Ejecutar `python main.py`

### CLI

- Ejecutar `python main.py --cli`
- Con semilla fija: `python main.py --cli --seed 42`
- Usar agente voraz: `python main.py --cli --agent greedy`
- Mostrar tablero completo: `python main.py --cli --show-board`

## Observaciones clave

- El proyecto combina generación de mapas, descenso de búsqueda en espacios parcialmente observables y visualización interactiva.
- Existen dos versiones de interfaz que comparten la misma lógica de reglas del juego.
- La versión web replica el comportamiento del agente de forma visual y accesible desde el navegador.
