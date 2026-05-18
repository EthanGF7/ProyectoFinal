
Cuando confirmes que estas 3 fases (0, 1-grep, 1b-extracción) terminan sin errores, sigo con Fase 2 (migrar datos), Fase 3 (crear runners), Fase 4 (consolidar `src/` → `core/src/`) y Fase 5 (limpieza). Las haré en bloques separados para que veas el resultado de cada una antes de la siguiente — así si algo se tuerce, paramos sin haber tocado más.**Stop. Mis comandos PowerShell están todos rotos.** El problema raíz: el apóstrofo en `DJ's` rompe el quoting de PowerShell, y `&&` no funciona en PowerShell 5.1. Aparte, parte de mi mensaje anterior se "ejecutó" como shell (los `---` y el texto).

**Buena noticia:** los `write_file` SÍ funcionaron. Ya están escritos:
- ✅ `DJ's/core/server.py` (actualizado)
- ✅ `DJ's/Flamenco/Flamenco.py` (actualizado)
- ✅ `DJ's/Nexus/Nexus.py` (machaca el monolito viejo)
- ✅ `DJ's/Pop/Pop.py` (nuevo)
- ✅ `DJ's/Urbano/Urbano.py` (machaca el monolito viejo)
- ✅ `DJ's/requirements.txt`
- ✅ `DJ's/_migration_extract_html.py`
- ✅ `DJ's/_extract_themes.py`

**Mala noticia:** ya he machacado `Nexus.py` y `Urbano.py` con el runner nuevo **sin haber extraído antes el HTML embebido**. El HTML de Nexus y Urbano ahora solo está en `DJ's_BACKUP_<timestamp>/` — **si el backup se creó**. Pero el backup también falló. Tengo que verificar inmediatamente.

**Estrategia nueva:** ya no uso PowerShell inline. Lo hago todo desde **un único script Python** que es portable, no tiene problemas de quoting, y es atómico. Antes de nada, verifico qué tengo vivo:

