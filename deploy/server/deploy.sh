#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 2 && $1 =~ ^[0-9a-f]{40}$ && $2 =~ ^sha256:[0-9a-f]{64}$ ]] || exit 64
readonly root=/opt/academic-platform
readonly revision=$1 digest=$2
readonly image="ghcr.io/caw111/softwareanalyse-api@$digest"
cd "$root"
exec 9>deploy.lock
flock -w 300 9 || { echo 'Another deployment is active.' >&2; exit 75; }

# The workflow sends two bounded lines; neither credential is a command-line argument.
IFS= read -r -t 15 -n 128 registry_user
IFS= read -r -t 15 -n 8192 registry_token
[[ $registry_user =~ ^[A-Za-z0-9-]{1,39}$ && ${#registry_token} -ge 20 && ${#registry_token} -lt 8192 ]] || exit 65
auth_dir=$(mktemp -d "$root/.registry-auth.XXXXXX")
export DOCKER_CONFIG=$auth_dir
cleanup() { unset registry_token; rm -f -- "$auth_dir/config.json"; rmdir -- "$auth_dir"; }
trap cleanup EXIT
printf '%s' "$registry_token" | docker login ghcr.io --username "$registry_user" --password-stdin >/dev/null
unset registry_token
docker pull "$image"
[[ $(docker image inspect "$image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}') == "$revision" ]] || {
  echo 'Image revision does not match the tested commit.' >&2; exit 65;
}

compose() { docker compose --env-file "$root/secrets.env" --env-file "$root/release.env" -f "$root/compose.yml" "$@"; }
mkdir -p backups releases
previous=false
if [[ -f release.env ]]; then
  cp release.env release.previous.env
  previous=true
  # Preserve the pre-migration database. Never restore a production database automatically.
  compose up -d --no-build --pull missing --wait --wait-timeout 90 db
  backup="backups/pre-${revision}-$(date -u +%Y%m%dT%H%M%SZ).dump"
  compose exec -T db pg_dump -U academic -d academic -Fc >"$backup.partial"
  mv "$backup.partial" "$backup"
fi
printf 'API_IMAGE=%s\nRELEASE_SHA=%s\n' "$image" "$revision" >release.next.env
mv release.next.env release.env
verify_release() {
  compose up -d --no-build --pull missing --wait --wait-timeout 180 &&
    curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8081/actuator/health/readiness >/dev/null &&
    curl --fail --silent --show-error --max-time 10 http://127.0.0.1:18081/api/reference >/dev/null &&
    curl --fail --silent --show-error --max-time 10 --noproxy '*' --cacert "$root/tls/server-ca.pem" --connect-to 49.233.93.248:8080:127.0.0.1:8080 https://49.233.93.248:8080/api/reference >/dev/null
}
if verify_release; then
  cp release.env "releases/${revision}.env"
  printf '%s %s %s success\n' "$(date -u +%FT%TZ)" "$revision" "$digest" >>deployments.log
  echo "Deployed $revision; readiness and public API passed."
else
  echo "Deployment $revision failed health verification." >&2
  if $previous; then
    cp release.previous.env release.env
    if verify_release; then
      echo 'Previous application image restored; database remains at its migrated schema.' >&2
    else
      echo 'Application rollback failed; operator intervention required. Database was not restored.' >&2
    fi
  fi
  printf '%s %s %s failed\n' "$(date -u +%FT%TZ)" "$revision" "$digest" >>deployments.log
  exit 1
fi
