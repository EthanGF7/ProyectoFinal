⚠️ Pero esto sobrescribiría mi `Nexus/Nexus.py` runner nuevo. Solución: lo **muevo** antes a un nombre temporal seguro, restauro el monolito de Nexus a un nombre temporal `_nexus_monolith.py`, y luego restauro el runner.

**Paso 2:** Adaptar `_extract_themes.py` para que lea de los nombres reales (`player.py` para Flamenco/Pop/Urbano, monolito de Nexus por separado).

**Paso 3:** Ejecutar la extracción → genera `djs/<DJ>/theme.html` para los 4.

**Paso 4:** Limpiar basura (`Flamenco.py` y `extract_themes.py` en raíz del repo, carpeta `s/`).

**Paso 5:** Seguir con migración de datos y limpieza final.

Voy con el rescate. Uso **solo Git y Python**, cero PowerShell con apóstrofos.

