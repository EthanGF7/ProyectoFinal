# 🎧 DJ AI — Sistema de Mezcla Automática Inteligente

> **Documento técnico y de presentación**
> Sistema modular de DJs virtuales que crean sesiones musicales coherentes usando inteligencia artificial sobre análisis musical previo.

---

## Índice

1. [Introducción](#1-introducción)
2. [Visión general del sistema](#2-visión-general-del-sistema)
3. [Arquitectura](#3-arquitectura)
4. [El concepto clave: el Arco Emocional](#4-el-concepto-clave-el-arco-emocional)
5. [El cerebro: cómo elige la siguiente canción](#5-el-cerebro-cómo-elige-la-siguiente-canción)
6. [Compatibilidad armónica: la rueda Camelot](#6-compatibilidad-armónica-la-rueda-camelot)
7. [Los cuatro estilos de mezcla](#7-los-cuatro-estilos-de-mezcla)
8. [El motor de audio en tiempo real](#8-el-motor-de-audio-en-tiempo-real)
9. [Los DJs disponibles](#9-los-djs-disponibles)
10. [Aprendizaje: el sistema de preferencias](#10-aprendizaje-el-sistema-de-preferencias)
11. [Flujo completo de una sesión](#11-flujo-completo-de-una-sesión)
12. [Características técnicas destacadas](#12-características-técnicas-destacadas)
13. [Guion para la presentación](#13-guion-para-la-presentación)
14. [Glosario](#14-glosario)

---

## 1. Introducción

### ¿Qué es DJ AI?

**DJ AI** es un sistema que reemplaza a un DJ humano. Dado un conjunto de canciones previamente analizadas, el sistema construye **una sesión completa coherente**: decide qué canción suena después, cuándo entra, cómo se mezcla con la anterior, y qué emoción transmite cada momento de la sesión.

### ¿Qué problema resuelve?

Un DJ humano hace dos cosas difíciles a la vez:

1. **Elegir la siguiente canción** que encaje musicalmente (BPM, tonalidad, energía) y emocionalmente (qué siente el público ahora).
2. **Ejecutar la transición** sin que se note el corte: cuándo bajar graves, cuándo cruzar el fader, cuándo introducir reverb.

DJ AI automatiza ambas tareas combinando reglas de teoría musical (rueda Camelot, BPM, energía) con un modelo de **arco emocional** de la sesión.

### ¿Para quién es?

- Eventos donde no hay DJ humano disponible
- Estudios de música para escuchar grandes bibliotecas de forma fluida
- Investigación sobre toma de decisiones musicales automáticas
- Cualquier persona que quiera escuchar su música como una sesión profesional, no como una playlist aleatoria

---

## 2. Visión general del sistema

DJ AI está compuesto por **DJs especializados**, cada uno con su propia personalidad musical:

| DJ | Estilo | Característica principal |
|---|---|---|
| 🎸 **Flamenco** | Flamenco fusión | Respeta los compases tradicionales |
| 🎵 **Pop** | Pop comercial | Transiciones limpias y energéticas |
| 🔥 **Urbano** | Reggaetón / Trap | Drops marcados, énfasis en graves |

**Todos comparten el mismo motor** (`core/`), pero cada uno tiene su propia biblioteca de canciones, su propia personalidad visual (`theme.html`) y aprende preferencias por separado.

### Lo que ve el usuario

Una **interfaz web** que se abre automáticamente en el navegador con:

- La canción actual con su BPM, tonalidad, energía y fase emocional
- La siguiente canción sugerida con su puntuación de compatibilidad
- Un botón **CUE** para previsualizar la siguiente
- Un botón **SKIP** para forzar la mezcla
- Una línea de tiempo con la sesión completa
- Visualización del waveform y la fase actual del arco

### Lo que pasa por debajo

1. Se cargan las canciones y su análisis musical previo (JSON con BPM, key, energía, puntos de mezcla)
2. Se calcula constantemente en qué fase del arco emocional estamos
3. Se puntúan todas las canciones candidatas y se elige una de las mejores
4. Se planifica la mezcla: en qué segundo empezar, qué estilo usar, cuánto durar
5. El motor de audio del navegador ejecuta la mezcla con curvas de fade reales

---

## 3. Arquitectura
