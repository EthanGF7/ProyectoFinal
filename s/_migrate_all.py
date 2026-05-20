
Si esto se ejecuta limpio, tendremos:
- ✅ HTML de los 4 DJs extraído a `djs/<DJ>/theme.html`
- ✅ Música y JSONs migrados
- ✅ Engines compartidos en `core/`
- ✅ Toda la basura borrada (musica/, src/, __pycache__/, monolitos, duplicados, ficheros sueltos en raíz del repo)

Si falla en Fase 1 (HTML), **aborta antes de borrar nada** — el script es defensivo. Si falla, te muestro qué pasó y ajustamos el regex.## Console Windows en cp1252 no traga emojis. Reemplazo todos por ASCII y reintento.

El script abortó **antes de borrar nada** (Fase 1 falló por print), así que estamos exactamente como antes. Limpio el script de unicode y lo reescribo:

