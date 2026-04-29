# Hunt the Wumpus 20x20 con IA

Proyecto en Python para generar partidas aleatorias de **Hunt the Wumpus** en una grilla de `20x20` y resolverlas con metodos de busqueda.

## Caracteristicas

- Mundo de `20x20` con agente, Wumpus, oro y pozos.
- Percepciones por cercania:
  - `hedor`: Wumpus adyacente.
  - `brisa`: pozo adyacente.
- Objetivo final: encontrar el oro.
- El agente puede matar al Wumpus con una flecha, pero eso no gana la partida.
- Generador aleatorio con semilla opcional.
- Validador que regenera el mapa hasta que exista solucion.
- IA exploratoria con A* para encontrar el oro usando percepciones y memoria.
- Opcion voraz/greedy para comparar estrategias.

## Uso con interfaz

### Version web responsiva

Abre este archivo en el navegador:

```bash
web/index.html
```

La version web esta optimizada para desktop con CSS Grid, panel lateral, tableros SVG escalables `1:1`, metricas y logs monoespaciados.

### Version Python/Tkinter

```bash
python main.py
```

La aplicacion de escritorio usa el mismo enfoque visual que la version web: layout desktop tipo dashboard, dos tableros escalables, panel lateral de control, metricas compactas y registro monoespaciado.

La aplicacion abre una ventana con:

- Dos perspectivas del tablero `20x20`:
  - Mundo completo: muestra Wumpus, oro, pozos, hedor, brisa y ruta.
  - Agente: empieza en blanco y solo muestra lo descubierto por la IA.
- Nueva semilla generada automaticamente con el boton `Nuevo juego`.
- Boton `Iniciar` para ejecutar la IA usando A* o Voraz.
- Panel con pasos usados, accion actual, recorrido del agente y registro de eventos.
- Ejecucion automatica: el jugador no controla movimientos ni disparos.
- La IA no conoce el mapa completo: decide con percepciones, memoria, celdas seguras y sospechas.

## Uso por consola

```bash
python main.py --cli
```

Con semilla fija:

```bash
python main.py --cli --seed 42
```

Usar busqueda voraz:

```bash
python main.py --cli --agent greedy
```

Mostrar el tablero completo:

```bash
python main.py --cli --show-board
```

## Estructura

- `main.py`: CLI para crear una partida, ejecutar la IA y mostrar el resultado.
- `web/index.html`: interfaz web responsiva para desktop.
- `web/styles.css`: layout moderno con CSS Grid/Flexbox, bento cards y tableros `1:1`.
- `web/app.js`: simulacion web del juego y animacion del agente.
- `wumpus/gui.py`: interfaz grafica interactiva con tablero y controles.
- `wumpus/game.py`: reglas del juego y estado de la partida.
- `wumpus/generator.py`: generacion aleatoria de mapas solucionables.
- `wumpus/agents.py`: IA con A* y busqueda voraz.

## Nota

La IA no conoce el mapa completo. Explora el tablero, registra percepciones, marca celdas seguras o sospechosas y toma decisiones con A* o busqueda voraz sobre su propio conocimiento.
