#!/bin/sh
# seed.sh -- reset the Mastodon fixture to its clean state and PROVE it.
#
# Clears every fault this case study can leave behind (paused containers,
# Sidekiq quiet or off the external network, the abort trigger, read-only
# Postgres, the antispam entry and its system report), then removes every
# status of the fixture user bob through the application's own
# RemoveStatusService (never the API: deletes are throttled 30 per 30 min),
# re-derives his post counter, and asserts the result. Exit 1 if any check
# fails. Takes ~20 s (rails runner boot).
#
#   sh EVALUATION/mastodon/seed.sh
set -u
BOB=117353415630680785
PSQL="docker exec -i mastodon-db-1 psql -U postgres -d mastodon_production -tA -v ON_ERROR_STOP=1 -c"

docker unpause mastodon-db-1 >/dev/null 2>&1
docker unpause mastodon-web-1 >/dev/null 2>&1
docker unpause mastodon-sidekiq-1 >/dev/null 2>&1
docker network connect mastodon_external_network mastodon-sidekiq-1 >/dev/null 2>&1

docker exec -i -e PGOPTIONS='-c default_transaction_read_only=off' mastodon-db-1 \
  psql -U postgres -tAc 'ALTER SYSTEM RESET default_transaction_read_only' >/dev/null
docker exec -i mastodon-db-1 psql -U postgres -tAc 'SELECT pg_reload_conf()' >/dev/null
sleep 1
$PSQL "DROP TRIGGER IF EXISTS fault_abort_write ON statuses; DROP FUNCTION IF EXISTS fault_abort_write();" >/dev/null
# Mastodon's own rate-limit counters (login throttle 25/h per e-mail, 300 posts
# per 3 h per account): test-environment counters, not behaviour under test
for k in $(docker exec mastodon-redis-1 redis-cli --scan --pattern 'cache:rack::attack:*') \
         $(docker exec mastodon-redis-1 redis-cli --scan --pattern 'rate_limit:*'); do
  docker exec mastodon-redis-1 redis-cli DEL "$k" >/dev/null
done
docker exec mastodon-redis-1 redis-cli SREM antispam:all_time_spammy_texts 'ioco note' >/dev/null

if [ "$(sh "$(dirname "$0")/sidekiq_state.sh")" != false ]; then
  docker restart mastodon-sidekiq-1 >/dev/null
  for i in $(seq 1 60); do
    [ "$(sh "$(dirname "$0")/sidekiq_state.sh")" = false ] && break; sleep 1
  done
fi

docker exec mastodon-web-1 bin/rails runner '
bob = Account.find_local("bob")
Status.unscoped.where(account_id: bob.id).find_each do |s|
  begin
    RemoveStatusService.new.call(s, immediate: true)
  rescue => e
    s.destroy
  end
end
Report.where(target_account_id: bob.id, account_id: -99).destroy_all
redis = Redis.new(url: ENV.fetch("REDIS_URL", "redis://redis:6379/0"))
key = "feed:home:#{bob.id}"
redis.zrange(key, 0, -1).each { |id| redis.zrem(key, id) unless Status.exists?(id: id) }
AccountStat.where(account_id: bob.id).update_all(statuses_count: Status.where(account_id: bob.id).count)
' 2>&1 | grep -v -i "warn" | head -5

fail=0
check () {  # name, command, expected
  got=$(sh -c "$2" 2>/dev/null | tr -d '[:space:]')
  if [ "$got" = "$3" ]; then echo "  ok    $1 = $got"; else echo "  FAIL  $1 = '$got' (want $3)"; fail=1; fi
}
echo "seed checks:"
check "bob statuses (incl. discarded)" "$PSQL \"SELECT count(*) FROM statuses WHERE account_id=$BOB\"" 0
check "bob statuses_count"             "$PSQL \"SELECT statuses_count FROM account_stats WHERE account_id=$BOB\"" 0
check "home feed size (alice's two)"    "docker exec mastodon-redis-1 redis-cli ZCARD feed:home:$BOB" 2
check "system reports on bob"          "$PSQL \"SELECT count(*) FROM reports WHERE target_account_id=$BOB AND account_id=-99\"" 0
check "abort trigger"                  "$PSQL \"SELECT count(*) FROM pg_trigger WHERE tgname='fault_abort_write'\"" 0
check "read-only default"              "$PSQL 'SHOW default_transaction_read_only'" off
check "antispam entry"                 "docker exec mastodon-redis-1 redis-cli SISMEMBER antispam:all_time_spammy_texts 'ioco note'" 0
check "db paused"                      "docker inspect -f '{{.State.Paused}}' mastodon-db-1" false
check "web paused"                     "docker inspect -f '{{.State.Paused}}' mastodon-web-1" false
check "sidekiq paused"                 "docker inspect -f '{{.State.Paused}}' mastodon-sidekiq-1" false
check "sidekiq on external network"    "docker inspect -f '{{range \$k,\$v := .NetworkSettings.Networks}}{{\$k}} {{end}}' mastodon-sidekiq-1 | grep -c external_network" 1
check "sidekiq live, not quiet"       "sh $(dirname "$0")/sidekiq_state.sh" false
check "rate-limit counters"          "docker exec mastodon-redis-1 redis-cli --scan --pattern 'cache:rack::attack:*' | grep -c . || true" 0
check "web health"                     "curl -sk --resolve mastodon.localhost:443:127.0.0.1 -o /dev/null -w '%{http_code}' https://mastodon.localhost/health" 200
exit $fail
