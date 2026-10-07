#!/bin/sh
# sidekiq_state.sh -- the quiet flag of every Sidekiq process whose heartbeat
# is fresh (< 20 s), sorted and de-duplicated: "false" (running), "true"
# (quiet), both, or nothing. A restarted container leaves its old process
# entry in Redis until it expires; counting it would report a worker that is
# gone. Sidekiq writes the flag on its heartbeat, every 10 s.
docker exec mastodon-redis-1 sh -c '
now=$(date +%s)
for p in $(redis-cli SMEMBERS processes); do
  b=$(redis-cli HGET "$p" beat | cut -d. -f1)
  [ -n "$b" ] && [ $((now - b)) -lt 20 ] && redis-cli HGET "$p" quiet
done' | sort -u | tr '\n' ' ' | sed 's/ $//'
