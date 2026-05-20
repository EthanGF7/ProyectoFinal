🎧 DJ AI — Sistema de Mezcla Automática Inteligente
Documento técnico y de presentación
Sistema modular de DJs virtuales que crean sesiones musicales coherentes usando inteligencia artificial sobre análisis musical previo.

Índice
Introducción
Visión general del sistema
Arquitectura
El concepto clave: el Arco Emocional
El cerebro: cómo elige la siguiente canción
Los cuatro estilos de mezcla
El motor de audio en tiempo real
Los DJs disponibles
Aprendizaje: el sistema de preferencias
Flujo completo de una sesión
Características técnicas destacadas
Glosario rápido
1. Introducción
¿Qué es DJ AI?
DJ AI es un sistema que reemplaza a un DJ humano. Dado un conjunto de canciones previamente analizadas, el sistema construye una sesión completa coherente: decide qué canción suena después, cuándo entra, cómo se mezcla con la anterior, y qué emoción transmite cada momento de la sesión.

¿Qué problema resuelve?
Un DJ humano hace dos cosas difíciles a la vez:

Elegir la siguiente canción que encaje musicalmente (BPM, tonalidad, energía) y emocionalmente (qué siente el público ahora).
Ejecutar la transición sin que se note el corte: cuándo bajar graves, cuándo cruzar el fader, cuándo introducir reverb.
DJ AI automatiza ambas tareas usando reglas de teoría musical (Camelot, BPM, energía) y un modelo de arco emocional de la sesión.

¿Para quién es?
Eventos donde no hay DJ humano disponible
Estudios de música para escuchar grandes bibliotecas de forma fluida
Investigación sobre toma de decisiones musicales automáticas
Cualquier persona que quiera escuchar su música como una sesión profesional, no como una playlist aleatoria
2. Visión general del sistema
DJ AI está compuesto por DJs especializados, cada uno con su propia personalidad musical:

| DJ | Estilo | Característica principal |
|---|---|---|
| 🎸 Flamenco | Flamenco fusión | Respeta los compases de bulería, soleá, etc. |
| 🎵 Pop | Pop comercial | Transiciones limpias y energéticas |
| 🔥 Urbano | Reggaetón / Trap | Drops marcados, énfasis en graves |
| 🌌 Nexus | Electrónica | Mezclas largas, atmósferas progresivas |

Todos comparten el mismo motor (core/), pero cada uno tiene su propia biblioteca de canciones, su propia personalidad visual (theme.html) y aprende preferencias por separado.

Lo que ve el usuario
Una interfaz web que se abre automáticamente en el navegador con:

La canción que suena actualmente con su BPM, tonalidad, energía y fase emocional
La siguiente canción sugerida con su puntuación de compatibilidad
Un botón CUE para previsualizar la siguiente
Un botón SKIP para forzar la mezcla
Una línea de tiempo con la sesión completa
Visualización del waveform y la fase actual del arco
Lo que pasa por debajo
Se cargan las canciones y su análisis musical previo (JSON con BPM, key, energía, puntos de mezcla)
Se calcula constantemente en qué fase del arco emocional estamos
Se puntúan todas las canciones candidatas y se elige la mejor
Se planifica la mezcla: en qué segundo empezar, qué estilo usar, cuánto durar
El motor de audio del navegador ejecuta la mezcla con curvas de fade reales
3. Arquitectura
DJ's/
├── core/                    🧠 MOTOR COMPARTIDO
│   ├── server.py            Servidor HTTP que sirve todo
│   ├── engine.js            Motor de audio Web Audio (cliente)
│   ├── arc.py               Arco emocional de la sesión
│   ├── mixing.py            Estilos de mezcla y duraciones
│   ├── scoring.py           Sistema de puntuación
│   ├── harmony.py           Compatibilidad armónica (Camelot)
│   ├── library.py           Carga biblioteca + JSONs de análisis
│   └── prefs.py             Persistencia de likes/dislikes
│
└── djs/                     🎭 DJs ESPECIALIZADOS
    ├── Flamenco/
    │   ├── canciones/       Archivos .mp3 / .wav
    │   ├── json/            Análisis musical (uno por canción)
    │   ├── theme.html       Interfaz visual del DJ
    │   └── preferencias.json
    ├── Pop/...
    └── Urbano/...
Decisión de diseño clave
El "cerebro" es Python (servidor). El "cuerpo" es JavaScript (navegador).

Python decide: qué suena después, cuándo, cómo, por qué
JavaScript ejecuta: reproduce, mezcla, aplica filtros y reverb, sincroniza BPM
Esto permite que toda la lógica musical compleja viva en Python (fácil de modificar, testear, extender) mientras que el audio se procesa con la Web Audio API nativa del navegador, sin necesidad de instalar nada extra.

Sin dependencias pesadas
El servidor usa únicamente la librería estándar de Python: http.server, json, urllib. No hay Flask, Django, ni frameworks. Esto significa:

Arranque instantáneo
Cero conflictos de versiones
Funciona en cualquier máquina con Python 3
Fácil de auditar y entender línea por línea
4. El concepto clave: el Arco Emocional
¿Qué es?
Una sesión de DJ profesional no es plana. Tiene una forma, un viaje emocional. DJ AI modela ese viaje en 7 fases:

Energía
 ▲
 │           ╱╲              ╱╲
 │          ╱  ╲            ╱  ╲___
 │         ╱    ╲          ╱
 │       ╱       ╲___    ╱
 │      ╱            ╲  ╱
 │   ╱
 │ ╱
 └───────────────────────────────────────────► Tiempo
   1️⃣      2️⃣      3️⃣       4️⃣      5️⃣      6️⃣      7️⃣
warm-up  build   peak-1  break  build-2  peak-2  outro
| Fase | Nombre interno | Energía objetivo | Qué pasa |
|---|---|---|---|
| 1 | warm-up | Baja (≈45) | Calentamiento, llegan los primeros |
| 2 | first-build | Media (≈60) | Subida progresiva |
| 3 | first-peak | Alta (≈80) | Primer clímax, todos bailando |
| 4 | breakdown | Media-baja (≈55) | Respiro emocional, momento íntimo |
| 5 | second-build | Media-alta (≈70) | Nueva subida |
| 6 | second-peak | Máxima (≈85) | Pico final, lo más energético |
| 7 | outro | Descenso (≈50) | Cierre suave |

¿Cómo se decide en qué fase estamos?
El módulo arc.py (función get_phase) recibe:

Cuántas canciones llevamos sonadas
Cuánto tiempo de sesión ha pasado
Y devuelve la fase actual junto con la energía objetivo que debería tener la siguiente canción. Esa energía objetivo es la brújula que guía toda la decisión.

¿Por qué importa?
Porque sin un arco, una sesión es solo una lista. Con arco, es una historia. El público no se cansa porque hay subidas y bajadas. El sistema de DJ AI no busca "la canción más parecida" — busca la canción correcta para este momento de la historia.

5. El cerebro: cómo elige la siguiente canción
Cada vez que termina (o está a punto de terminar) la canción actual, el servidor ejecuta pick_next() en scoring.py. Este es el corazón del sistema.

Pasos
1. Filtrado
Se descartan:

Canciones ya reproducidas en esta sesión
Canciones con energía muy alejada del objetivo de la fase actual
Canciones con BPM incompatible (diferencia > ~10 BPM)
2. Puntuación
Cada candidata recibe una puntuación de 0 a 100 que combina varios factores:

| Factor | Peso | Qué mide |
|---|---|---|
| Energía | Alto | Cercanía a la energía objetivo de la fase |
| Armonía (Camelot) | Alto | Compatibilidad de tonalidades musicales |
| BPM | Medio | Diferencia de tempo (más cerca = mejor) |
| Preferencias | Medio | +bonus si tiene 👍, -penalización si tiene 👎 |
| Diversidad | Bajo | Penaliza repetir el mismo artista seguido |

3. Selección
La canción con mayor puntuación gana y se devuelve al navegador junto con su plan de mezcla.

¿Qué es Camelot?
Es el sistema estándar mundial de DJs para representar tonalidades. Asigna a cada tonalidad un código tipo 8A, 11B, etc.

Reglas:

Mismo número, misma letra = misma tonalidad → encajan perfecto
Mismo número, distinta letra = mayor↔menor relativos → muy compatible
Número adyacente (±1), misma letra = compatibles (quintas)
Saltos grandes = chocan, suenan mal
harmony.py implementa esta lógica y la convierte en una puntuación numérica.

6. Los cuatro estilos de mezcla
No todas las transiciones se hacen igual. DJ AI tiene 4 estilos que aplica según el contexto. Esto es lo que da carácter al sistema.

⚡ Guetta — Agresivo
Cuándo: picos de energía, BPM alto, momento de máxima euforia
Duración: 9–14 segundos (corta)
Característica: swap brusco de graves, drop duro
Curva: fade lineal con corte fuerte al 70%
Sensación: "¡bum! cambio limpio"
🌅 Avicii — Melódico
Cuándo: breakdowns, transiciones emocionales, energías bajas o saltos grandes
Duración: 14–22 segundos (media-larga)
Característica: mucho reverb (35%), filtros suaves
Curva: ease-in-out cuadrática
Sensación: "fluye como un atardecer"
〰 Progressive — Técnico
Cuándo: BPMs casi idénticos (±3), energías similares
Duración: 16–20 segundos (larga)
Característica: intercambio gradual de frecuencias (low-pass una baja, high-pass la otra sube)
Curva: ease-in-out cúbica perfectamente simétrica
Sensación: "no notas dónde acaba una y empieza la otra"
✦ Fusion — Coexistencia
Cuándo: BPM muy similar (±6) + energía compatible, momento experimental
Duración: 32–38 segundos (la más larga)
Característica: las dos canciones coexisten durante mucho tiempo
Curva: ease-in-out quíntica
Sensación: "dos canciones tocan a la vez sin pelearse"
¿Cómo se elige el estilo?
mixing.py → detect_style() aplica esta lógica:

¿BPM casi idéntico y energías compatibles?  → fusion / progressive
¿Estamos en breakdown?                      → avicii
¿Energía baja o BPM lento?                  → avicii
¿Salto grande de energía?                   → avicii
¿Pico de energía con BPM alto?              → guetta
Por defecto:                                → guetta
7. El motor de audio en tiempo real
Toda la reproducción ocurre en el navegador usando la Web Audio API. No hay reproductor externo.

La cadena de audio
Canción A ─┐
           ├─→ preGain ─→ HighPass ─→ LowPass ─→ Analyser ─┐
Canción B ─┘                                                │
                                                            ├─→ Compressor ─→ 🔊
                                          ┌─────────────────┘
                                          └─→ ReverbGain ─→ Convolver ─→ 🔊
Componentes
Dos decks (A y B): simulan los dos platos de un DJ
preGain: controla el volumen de cada deck (sube uno, baja el otro)
High-pass / Low-pass: filtros que quitan graves o agudos durante la mezcla
Analyser: detecta el RMS para análisis de beats
Compressor maestro: evita picos y mantiene volumen consistente
Convolver de reverb: genera reverb con un impulse response sintético de 2.5s
Durante la mezcla
Mientras suena la canción saliente, el motor:

Carga la entrante en el deck contrario
Sincroniza el BPM usando playbackRate (acelera o ralentiza la entrante)
Aplica la curva del estilo elegido a preGain de ambos decks
Filtra graves de la saliente progresivamente
Ajusta reverb según el estilo (Avicii sube hasta 35%, Guetta solo 18%)
Desliza el playbackRate hacia 1.0 para que la entrante recupere su tempo natural
Todo esto está programado al milisegundo usando setValueAtTime() y rampas exponenciales del Web Audio.

Función CUE
El botón CUE permite previsualizar la siguiente canción sin que la oiga el público. En este sistema, como solo hay una salida, se reproduce 8 segundos del punto de entrada planificado para que el operador valide la mezcla.

8. Los DJs disponibles
🎸 Flamenco
Especializado en flamenco fusión: bulerías, rumbas, tangos, soleás modernos. Respeta los compases tradicionales (12 pulsos en bulería, etc.) y prefiere transiciones largas tipo Avicii para mantener el "duende".

🎵 Pop
Pop comercial actual, ideal para fiestas amplias. Privilegia mezclas tipo Guetta con drops claros, energía sostenida y tonalidades compatibles.

🔥 Urbano
Reggaetón, trap, hip-hop. Mezclas cortas y enérgicas, énfasis en el grave, BPM típicamente 90–100 (medio tiempo) que se dobla mentalmente a 180–200.

🌌 Nexus
Electrónica progresiva, house, techno. Aquí brilla el estilo progressive y fusion: mezclas larguísimas, atmósferas, builds infinitos.

¿Cómo añadir un DJ nuevo?
Crear carpeta djs/MiDJ/
Añadir subcarpetas canciones/ y json/
Crear theme.html con la interfaz visual (debe definir window.initTheme() y window.drawTheme())
Lanzar: python -m core.server MiDJ
El sistema es plug-and-play.

9. Aprendizaje: el sistema de preferencias
Cada DJ tiene su propio archivo preferencias.json donde guarda:

{
  "cancion1.mp3": 1,    // 👍 like
  "cancion2.mp3": -1,   // 👎 dislike
  "cancion3.mp3": 1
}
Cómo afecta
+1 (like): la canción suma puntos en el scoring → aparece antes
-1 (dislike): resta puntos → casi nunca se elige
Persistente entre sesiones: el DJ "recuerda" lVoy a crear un documento técnico completo. Primero reviso un par de archivos más para que la documentación sea 100% precisa: