#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

web_url="http://127.0.0.1:7878"
docker compose exec -T api sh -c \
  'mkdir -p /var/lib/hynomas/settings && touch /var/lib/hynomas/settings/restart-probe'

gallery_before="$(curl --fail --silent --show-error "$web_url/v1/gallery" | jq '.items | length')"
test "$gallery_before" -gt 0

upload="$(curl --fail --silent --show-error \
  -H 'Content-Type: image/png' \
  --data-binary '@apps/frontend/public/hunyuan-logo.png' \
  "$web_url/v1/reference-images?perspective=third-person%20follow")"
image_id="$(jq -r '.id // empty' <<<"$upload")"
test -n "$image_id"

for _ in $(seq 1 20); do
  caption_status="$(curl --fail --silent --show-error \
    "$web_url/v1/reference-images/$image_id" | jq -r '.caption_status // empty')"
  [[ "$caption_status" == "ready" ]] && break
  sleep 1
done
test "${caption_status:-}" = "ready"
test -s "$root/outputs/web/reference_images/$image_id.jpg"

docker compose restart
ready=false
for _ in $(seq 1 30); do
  if status="$(curl --silent --show-error "$web_url/health" 2>/dev/null)" \
    && [[ "$(jq -r '.worker_status // empty' <<<"$status")" == "ready" ]]; then
    ready=true
    break
  fi
  sleep 2
done
test "$ready" = true

test "$(curl --fail --silent --show-error \
  "$web_url/v1/reference-images/$image_id" | jq -r '.caption_status')" = "ready"
gallery_after="$(curl --fail --silent --show-error "$web_url/v1/gallery" | jq '.items | length')"
test "$gallery_after" -ge "$gallery_before"
docker compose exec -T api test -f /var/lib/hynomas/settings/restart-probe

printf 'persisted_image_id=%s gallery_before=%s gallery_after=%s\n' \
  "$image_id" "$gallery_before" "$gallery_after"
