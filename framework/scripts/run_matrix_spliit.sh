#!/usr/bin/env bash
export PROJECT="/Users/ayobamidele/text-conc"

# Kill any leftover processes on the proxy and browser ports
lsof -ti:3002 | xargs kill -9 2>/dev/null
pkill -f chromedriver 2>/dev/null
sleep 1

cd "$PROJECT"

# Start the fault-injection proxy (Spliit must already be running on :3000)
source .venv/bin/activate 2>/dev/null || true
python systems/spliit/sut/fault_middleware.py &
PROXY_PID=$!

for i in {1..15}; do
  curl -s http://localhost:3002/ > /dev/null && break
  sleep 1
done
echo "Fault proxy started (PID $PROXY_PID)"

mkdir -p generated/logs
LOG="generated/logs/spliit_taxonomy_matrix.log"
RESULTS="$PROJECT/generated/spliit_results.json"
echo "========================================" > "$LOG"
echo "Spliit taxonomy matrix run — $(date)"    >> "$LOG"
echo "========================================" >> "$LOG"

write_results_json() {
  python3 -c "
import re, json, sys
log = open(sys.argv[1]).read()
strip = lambda s: re.sub(r'\x1b\[[0-9;]*m', '', s)
results = {}
key = None
for line in log.split('\n'):
    line = strip(line).strip()
    m = re.match(r'^KEY:\s+(.+)$', line)
    if m: key = m.group(1).strip(); continue
    m = re.match(r'^Verdict:\s+(FAIL|PASS|INCONC)', line)
    if m and key: results[key] = m.group(1); key = None
with open(sys.argv[2], 'w') as f:
    json.dump(results, f, indent=2)
" "$LOG" "$RESULTS" 2>/dev/null
}

reset_proxy() {
  curl -s -X POST http://localhost:3002/admin/fault/reset > /dev/null
  pkill -f chromedriver 2>/dev/null
  sleep 1
}

BASE_ARGS=(
  --aut        systems/spliit/model/tc_a4.aut
  --platform   html
  --url        http://localhost:3002
  --system-interface   systems/spliit/model/system_interface_spliit.lnt
  --type-description   systems/spliit/properties/type_description.yml
  --verbose
)

BASE_ARGS_U1=(
  --aut        systems/spliit/model/tc_u1.aut
  --platform   html
  --url        http://localhost:3002
  --system-interface   systems/spliit/model/system_interface_spliit.lnt
  --type-description   systems/spliit/properties/type_description.yml
  --verbose
)

MAPPING=systems/spliit/properties/disruption_mapping.yml

run_disruption() {
  local KEY="$1"
  echo ""                                       | tee -a "$LOG"
  echo "--------------------------------------" | tee -a "$LOG"
  echo "KEY: $KEY"                             | tee -a "$LOG"
  echo "TIME: $(date)"                         | tee -a "$LOG"
  echo "--------------------------------------" | tee -a "$LOG"
  reset_proxy
  PYTHONPATH="$PWD/framework" python framework/scripts/run.py \
    "${BASE_ARGS[@]}" \
    --disruption-mapping "$MAPPING" \
    --disruption-key     "$KEY" \
    2>&1 | tee -a "$LOG"
  echo "EXIT: $?" | tee -a "$LOG"
}

run_normal() {
  echo ""                                       | tee -a "$LOG"
  echo "--------------------------------------" | tee -a "$LOG"
  echo "KEY: NORMAL (no disruption)"           | tee -a "$LOG"
  echo "TIME: $(date)"                         | tee -a "$LOG"
  echo "--------------------------------------" | tee -a "$LOG"
  reset_proxy
  PYTHONPATH="$PWD/framework" python framework/scripts/run.py \
    "${BASE_ARGS[@]}" \
    2>&1 | tee -a "$LOG"
  echo "EXIT: $?" | tee -a "$LOG"
}

run_ue1_offline() {
  echo ""                                       | tee -a "$LOG"
  echo "--------------------------------------" | tee -a "$LOG"
  echo "KEY: UE1_OFFLINE (client offline)"     | tee -a "$LOG"
  echo "TIME: $(date)"                         | tee -a "$LOG"
  echo "--------------------------------------" | tee -a "$LOG"
  reset_proxy
  PYTHONPATH="$PWD/framework" python framework/scripts/run.py \
    "${BASE_ARGS_U1[@]}" \
    2>&1 | tee -a "$LOG"
  echo "EXIT: $?" | tee -a "$LOG"
}

KEYS=(
  "DISRUPTION_OCCURS !SENSOR_TIMEOUT (AMOUNT_INPUT)"
  "DISRUPTION_OCCURS !SENSOR_PARTIAL_FAIL (BALANCE_CALCULATOR)"
  "DISRUPTION_OCCURS !SENSOR_IMPRECISION (AMOUNT_NOISE_SPIKE)"
  "DISRUPTION_OCCURS !SENSOR_NOISE (SPLIT_NOTIFIER)"
  "DISRUPTION_OCCURS !SENSOR_INACCURACY (AMOUNT_BIAS_MINUS10)"
  "DISRUPTION_OCCURS !ENVIRONMENT_OBSTACLE (NETWORK_PARTITION)"
  "DISRUPTION_OCCURS !ENVIRONMENT_OBSTACLE (SESSION_TIMEOUT)"
  "DISRUPTION_OCCURS !ENVIRONMENT_AMBIGUITY (CONCURRENT_WRITE)"
  "DISRUPTION_OCCURS !ENVIRONMENT_UNKNOWN (MESSAGE_DELIVERY_FAIL)"
)

for KEY in "${KEYS[@]}"; do
  run_disruption "$KEY"
  write_results_json
done

run_normal
write_results_json

run_ue1_offline
write_results_json

echo ""
echo "========================================"
echo "RESULTS SUMMARY"
echo "========================================"
grep -E "^KEY:|Verdict:" "$LOG" | paste - -

kill $PROXY_PID 2>/dev/null
pkill -f chromedriver 2>/dev/null
echo "Done. Full log: $LOG"
