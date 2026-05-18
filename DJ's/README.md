# DJ AI Player

Sistema modular de DJs automaticos con analisis de audio.

## Estructura

    DJs/
    |- core/         Logica compartida (server, library, scoring, ...)
    |- djs/          Musica + tema por DJ
    |   |- Flamenco/   canciones/ json/ theme.html preferencias.json
    |   |- Pop/        idem
    |   |- Urbano/     idem
    |- Flamenco/     Lanzador: Flamenco.py
    |- Pop/          Lanzador: POP.py
    |- Urbano/       Lanzador: Urbano.py
    |- Nexus/        Variante monolitica independiente (engines avanzados)
    |- requirements.txt   Dependencias unificadas
    |- README_DJAI.docx   Documentacion completa

## Uso

    pip install -r requirements.txt

    python "Pop/POP.py"            # http://localhost:8767
    python "Urbano/Urbano.py"      # http://localhost:8768
    python "Flamenco/Flamenco.py"  # http://localhost:8765
    python "Nexus/Nexus.py"        # variante independiente

Consulta README_DJAI.docx para la documentacion completa.
