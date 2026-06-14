#!/usr/bin/env bash
# start.sh — Levanta los servicios de FutBotMX localmente.
#
# Uso:
#   ./start.sh                    # usa experiment más reciente
#   ./start.sh experiments/test_034_full_analysis
#
# Servicios:
#   http://127.0.0.1:8766  → Live Playback App (video + overlay + analytics)
#
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv/bin/python"
if [ ! -f "$VENV" ]; then
  echo "ERROR: entorno virtual no encontrado en .venv/"
  echo "       Corre: python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

# Cargar variables de entorno
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

# Determinar experimento
if [ $# -ge 1 ]; then
  EXPERIMENT="$1"
else
  # Usar el experimento con level3_tracks.csv más reciente
  EXPERIMENT=$(find experiments -name "level3_tracks.csv" -printf "%T@ %h\n" 2>/dev/null \
    | sort -n | tail -1 | awk '{print $2}' | xargs -I{} dirname {} 2>/dev/null || echo "")
  if [ -z "$EXPERIMENT" ]; then
    echo "ERROR: no se encontró ningún experimento con level3_tracks.csv"
    echo "       Corre primero: python scripts/run_unified_analysis.py --video \$FUTBOTMX_VIDEO_836 --clip-id video_836"
    exit 1
  fi
fi

TRACKS="$EXPERIMENT/level3_spatial/level3_tracks.csv"
EVENTS="$EXPERIMENT/level3_events/level3_events.json"
HIGHLIGHTS="$EXPERIMENT/level3_events/level3_highlights.csv"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FutBotMX — Servicios locales"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Experimento : $EXPERIMENT"
echo "  Tracks      : $TRACKS"
echo ""

if [ ! -f "$TRACKS" ]; then
  echo "WARN: $TRACKS no existe — el overlay no tendrá datos de tracking."
  echo "      Ejecuta el pipeline completo primero."
fi

# Matar instancias anteriores
pkill -f "run_live_playback_app" 2>/dev/null || true
sleep 0.5

# Levantar live_playback_app
TRACKS_ARG=""
EVENTS_ARG=""
HIGHLIGHTS_ARG=""
[ -f "$TRACKS" ]     && TRACKS_ARG="--tracks-csv $TRACKS"
[ -f "$EVENTS" ]     && EVENTS_ARG="--events-json $EVENTS"
[ -f "$HIGHLIGHTS" ] && HIGHLIGHTS_ARG="--highlights-csv $HIGHLIGHTS"

PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}" \
  "$VENV" scripts/run_live_playback_app.py \
    $TRACKS_ARG $EVENTS_ARG $HIGHLIGHTS_ARG \
    --port 8766 &

LP_PID=$!
sleep 2

echo ""
echo "  ✓  Live Playback App  →  http://127.0.0.1:8766"
echo ""
echo "  Para analizar un video distinto, usa el formulario en la parte"
echo "  superior de la interfaz o ejecuta:"
echo ""
echo "    python scripts/run_unified_analysis.py \\"
echo "      --video \"\$FUTBOTMX_VIDEO_836\" --clip-id video_836 \\"
echo "      --start-frame 120 --end-frame 180"
echo ""
echo "  Presiona Ctrl+C para detener."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Abrir navegador
xdg-open "http://127.0.0.1:8766" 2>/dev/null || open "http://127.0.0.1:8766" 2>/dev/null || true

# Esperar
wait $LP_PID
