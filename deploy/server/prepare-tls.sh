#!/usr/bin/env bash
# Run on the server. Only server-ca.pem is distributed with the desktop app.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 ]] || exit 1
root=/opt/academic-platform/tls
install -d -m 700 "$root"
install -d -m 750 -o root -g 101 "$root/edge"
cd "$root"
exec 9>.cert.lock
flock 9
stage=$(mktemp -d "$root/.new.XXXXXX")
trap 'rm -f -- "$stage"/{ca.key,ca.pem,server.key,server.csr,server.pem,ext}; rmdir -- "$stage"' EXIT
if [[ ! -f server-ca.pem && ! -f ca.key && ${1:-} == --init ]]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -sha256 -days 3650 \
    -subj '/CN=Academic Platform API Root' -addext 'basicConstraints=critical,CA:TRUE,pathlen:0' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' -keyout "$stage/ca.key" -out "$stage/ca.pem"
  install -m 600 "$stage/ca.key" ca.key
  install -m 644 "$stage/ca.pem" server-ca.pem
fi
[[ -s ca.key && -s server-ca.pem ]] || { echo 'Restore the existing CA or explicitly initialize a new installation.' >&2; exit 1; }
openssl x509 -in server-ca.pem -noout -checkend 34560000 >/dev/null || { echo 'Rotate the desktop trust anchor before issuing a new leaf.' >&2; exit 1; }
if [[ -s edge/server.pem && -s edge/server.key ]] &&
   openssl x509 -in edge/server.pem -noout -checkend 2592000 >/dev/null &&
   openssl verify -CAfile server-ca.pem -purpose sslserver -verify_ip 49.233.93.248 edge/server.pem >/dev/null; then
  exit 0
fi
openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
  -subj '/CN=Academic Platform API' -keyout "$stage/server.key" -out "$stage/server.csr"
cat > "$stage/ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=IP:49.233.93.248
EOF
openssl x509 -req -sha256 -days 397 -in "$stage/server.csr" -CA server-ca.pem -CAkey ca.key \
  -set_serial "0x$(openssl rand -hex 16)" -extfile "$stage/ext" -out "$stage/server.pem"
openssl verify -CAfile server-ca.pem -purpose sslserver -verify_ip 49.233.93.248 "$stage/server.pem"
install -m 640 -o root -g 101 "$stage/server.key" edge/server.next.key
install -m 644 "$stage/server.pem" edge/server.next.pem
mv edge/server.next.key edge/server.key
mv edge/server.next.pem edge/server.pem
# A running nginx keeps its current pair in memory until this verified pair is loaded.
proxy=$(docker ps --filter label=com.docker.compose.project=academic-platform \
  --filter label=com.docker.compose.service=gateway --format '{{.ID}}')
if [[ -n $proxy ]]; then docker exec "$proxy" nginx -t; docker kill --signal=HUP "$proxy" >/dev/null; fi
