#!/usr/bin/env bash
# connect-gemini.sh — connects Mate to the Gemini API free tier.
#
# Usage:  bash connect-gemini.sh /path/to/mate      (or run it inside the mate folder)
#
# 1. Asks for your Gemini API key (typing is hidden; press Enter to keep the key already in .env).
# 2. Asks Google which models this key can use and lets you pick one (a Flash model is suggested).
# 3. Sends one tiny test request to that model to prove it answers in JSON.
# 4. Saves MODEL_PROVIDER, GEMINI_API_KEY and GEMINI_MODEL to .env (git-ignored), restarts Mate
#    and shows whether the backend is connected.
set -euo pipefail

API="https://generativelanguage.googleapis.com/v1beta"
TARGET="${1:-.}"
cd "$TARGET"
if [[ ! -f docker-compose.yml || ! -d backend/app ]]; then
  echo "This is not the Mate folder: $(pwd)"; echo "Run: bash connect-gemini.sh /path/to/mate"; exit 1
fi
if ! grep -q "GEMINI_API_KEY" docker-compose.yml; then
  echo "This Mate folder does not have the Gemini update yet. Run apply-gemini-update.sh first."; exit 1
fi

[[ -f .env ]] || cp .env.example .env
CURRENT_KEY="$(grep -E '^GEMINI_API_KEY=' .env | head -1 | cut -d= -f2- || true)"
CURRENT_MODEL="$(grep -E '^GEMINI_MODEL=' .env | head -1 | cut -d= -f2- || true)"

echo "Paste your Gemini API key from https://aistudio.google.com/apikey"
[[ -n "$CURRENT_KEY" ]] && echo "(press Enter to keep the key already saved in .env)"
read -r -s -p "Key: " KEY; echo
KEY="$(printf '%s' "${KEY:-$CURRENT_KEY}" | tr -d '[:space:]\"'"'")"
[[ -z "$KEY" ]] && { echo "No key entered."; exit 1; }

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
message() { grep -o '"message": *"[^"]*"' "$1" | head -1 | sed 's/"message": *//' || true; }

# --- 1. Which models can this key use? ----------------------------------------------------------
echo "Asking Google which models this key can use..."
CODE="$(curl -s -o "$WORK/models.json" -w '%{http_code}' --max-time 20 \
  -H "x-goog-api-key: $KEY" "$API/models?pageSize=1000" || echo 000)"
case "$CODE" in
  200) ;;
  000) echo "Could not reach Google (no internet, VPN or firewall?). Fix the connection and run this again."; exit 1 ;;
  *)   echo "Google refused to list models for this key (HTTP $CODE): $(message "$WORK/models.json")"
       echo "Nothing was changed. In AI Studio, click 'Copy cURL quickstart' on the key and share that command"
       echo "with the key replaced by YOUR_KEY, so Mate can be adjusted to it."
       exit 1 ;;
esac

grep -o '"name": *"models/[^"]*"' "$WORK/models.json" | sed 's/.*"models\///; s/"$//' | sort -u > "$WORK/all.txt"
# Text models suited to Mate: Gemini Flash/Pro chat models, no image/audio/TTS/live/embedding variants.
grep -E '^gemini-' "$WORK/all.txt" | grep -Ev 'image|tts|audio|live|embedding|vision|thinking-exp|native|computer-use|robotics' \
  > "$WORK/text.txt" || true
{
  grep -E '^gemini-flash-latest$' "$WORK/text.txt" || true
  grep -E 'flash' "$WORK/text.txt" | grep -Ev 'lite|latest' | sort -r || true
  grep -E 'flash-lite' "$WORK/text.txt" | sort -r || true
  grep -Ev 'flash' "$WORK/text.txt" | sort -r || true
} | awk '!seen[$0]++' > "$WORK/candidates.txt"

if [[ ! -s "$WORK/candidates.txt" ]]; then
  echo "Google returned no Gemini text models for this key. Models it did list:"; cat "$WORK/all.txt"; exit 1
fi

DEFAULT="$(head -1 "$WORK/candidates.txt")"
if [[ -n "$CURRENT_MODEL" ]] && grep -qx "$CURRENT_MODEL" "$WORK/candidates.txt"; then DEFAULT="$CURRENT_MODEL"; fi

echo
echo "Models this key can use (Flash models are fast and have the most free quota):"
n=0
while IFS= read -r m; do
  n=$((n+1)); [[ $n -gt 15 ]] && break
  marker=""; [[ "$m" == "$DEFAULT" ]] && marker="   <- suggested"
  printf '  %2d) %s%s\n' "$n" "$m" "$marker"
done < "$WORK/candidates.txt"
read -r -p "Choose a number, or press Enter for the suggested model: " CHOICE
if [[ -n "${CHOICE:-}" ]]; then
  MODEL="$(sed -n "${CHOICE}p" "$WORK/candidates.txt")"
  [[ -z "$MODEL" ]] && { echo "Not a valid choice."; exit 1; }
else
  MODEL="$DEFAULT"
fi

# --- 2. Prove the model answers in JSON -----------------------------------------------------------
test_model() {
  curl -s -o "$WORK/test.json" -w '%{http_code}' --max-time 60 \
    -H "x-goog-api-key: $KEY" -H "Content-Type: application/json" \
    -d '{"contents":[{"role":"user","parts":[{"text":"Reply with the JSON object {\"ok\": true} and nothing else."}]}],"generationConfig":{"responseMimeType":"application/json"}}' \
    "$API/models/$1:generateContent" || echo 000
}
echo "Testing $MODEL with one tiny request..."
CODE="$(test_model "$MODEL")"
case "$CODE" in
  200) echo "It answered. $MODEL works with your key." ;;
  429) echo "The model exists but the free quota is used up right now (HTTP 429). Saving it; try Mate again in a minute." ;;
  *)   echo "$MODEL did not work (HTTP $CODE): $(message "$WORK/test.json")"
       echo "Run the script again and pick another model from the list. Nothing was changed."; exit 1 ;;
esac

# --- 3. Save and restart ---------------------------------------------------------------------------
awk -v key="$KEY" -v model="$MODEL" '
  /^GEMINI_API_KEY=/ { print "GEMINI_API_KEY=" key; k=1; next }
  /^GEMINI_MODEL=/   { print "GEMINI_MODEL=" model; m=1; next }
  /^MODEL_PROVIDER=/ { print "MODEL_PROVIDER=gemini"; p=1; next }
  { print }
  END { if (!p) print "MODEL_PROVIDER=gemini"; if (!k) print "GEMINI_API_KEY=" key; if (!m) print "GEMINI_MODEL=" model }
' .env > "$WORK/env"
cp "$WORK/env" .env
chmod 600 .env
echo "Saved to .env: MODEL_PROVIDER=gemini, GEMINI_MODEL=$MODEL and your key."

echo "Restarting Mate..."
docker compose up -d --build

echo "Waiting for the backend..."
STATUS=""
for _ in $(seq 1 45); do
  STATUS="$(curl -s --max-time 15 http://localhost:8000/api/system/status || true)"
  [[ "$STATUS" == *'"provider"'* ]] && break
  sleep 2
done
[[ "$STATUS" == *'"provider"'* ]] || { echo "The backend did not answer. See: docker compose logs backend"; exit 1; }

field() {
  local v
  v="$(printf '%s' "$STATUS" | grep -o "\"$1\": *\"[^\"]*\"" | head -1 | cut -d: -f2- || true)"
  [[ -z "$v" ]] && v="$(printf '%s' "$STATUS" | grep -o "\"$1\": *[a-z0-9]*" | head -1 | cut -d: -f2- || true)"
  printf '%s' "$v" | sed 's/^ *//'
}
echo
echo "Provider:   $(field provider)"
echo "Model:      $(field model)"
echo "Connected:  $(field model_installed)"
DETAIL="$(field detail)"; [[ -n "$DETAIL" && "$DETAIL" != "null" ]] && echo "Detail:     $DETAIL"
echo
if [[ "$(field model_installed)" == "true" ]]; then
  echo "Mate is connected. Open http://localhost:8080 — in an existing live venture, click 'Analyse my profile'"
  echo "again, or start a new venture with the live model."
else
  echo "Not connected yet. Check the detail above, or run: docker compose logs backend"
fi
