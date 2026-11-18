#!/usr/bin/env bash
# First deployment only. Subsequent releases use the restricted CI gateway.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 2 && $1 =~ ^sha256:[0-9a-f]{64}$ && $2 =~ ^[0-9a-f]{40}$ ]] || exit 64
readonly root=/opt/academic-platform image=$1 revision=$2
cd "$root"
exec 9>deploy.lock
flock -w 300 9
[[ ! -e release.env ]] || { echo 'A release already exists; use the deployment gateway.' >&2; exit 65; }
[[ $(docker image inspect "$image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}') == "$revision" ]] || exit 65
printf 'API_IMAGE=%s\nRELEASE_SHA=%s\n' "$image" "$revision" >release.env
docker compose --env-file secrets.env --env-file release.env -f compose.yml up -d --no-build --pull missing --wait --wait-timeout 180
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8081/actuator/health/readiness
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8080/api/reference >/dev/null
mkdir -p releases
cp release.env "releases/${revision}.env"
printf '%s %s %s bootstrap\n' "$(date -u +%FT%TZ)" "$revision" "$image" >>deployments.log
echo 'First server deployment is healthy.'
