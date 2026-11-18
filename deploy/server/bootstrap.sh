#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 1 && -f $1 ]] || { echo 'Usage: sudo bash bootstrap.sh dedicated-deploy-key.pub' >&2; exit 64; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly root=/opt/academic-platform
install -d -m 750 "$root"
install -d -m 755 /usr/local/lib/academic-platform
install -m 644 "$source_dir/compose.yml" "$root/compose.yml"
install -m 755 "$source_dir/deploy.sh" /usr/local/sbin/academic-deploy
install -m 755 "$source_dir/ssh-deploy-gateway.py" /usr/local/lib/academic-platform/ssh-deploy-gateway
if [[ ! -f $root/secrets.env ]]; then
  python3 - "$root/secrets.env" <<'PY'
import os, secrets, sys
path = sys.argv[1]
with open(path, 'x', encoding='utf-8') as output:
    output.write('DB_PASSWORD=' + secrets.token_hex(32) + '\n')
    output.write('ADMIN_PASSWORD=' + secrets.token_urlsafe(32) + '\n')
    output.write('CRAWL_CONTACT_EMAIL=\n')
os.chmod(path, 0o600)
PY
fi
id academic-deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash academic-deploy
install -d -m 700 -o academic-deploy -g academic-deploy /home/academic-deploy/.ssh
python3 - "$1" /home/academic-deploy/.ssh/authorized_keys <<'PY'
import os, pathlib, re, sys
key = pathlib.Path(sys.argv[1]).read_text().strip()
if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]+)?', key):
    raise SystemExit('Expected one dedicated Ed25519 public key')
entry = 'restrict,command="/usr/local/lib/academic-platform/ssh-deploy-gateway" ' + key
path = pathlib.Path(sys.argv[2])
existing = path.read_text().splitlines() if path.exists() else []
if not any(key.split()[1] in line.split() for line in existing):
    with path.open('a') as output:
        output.write(entry + '\n')
os.chmod(path, 0o600)
PY
chown academic-deploy:academic-deploy /home/academic-deploy/.ssh/authorized_keys
sudo_rule=$(mktemp)
printf 'academic-deploy ALL=(root) NOPASSWD: /usr/local/sbin/academic-deploy\n' >"$sudo_rule"
visudo -cf "$sudo_rule"
install -m 440 "$sudo_rule" /etc/sudoers.d/academic-platform-deploy
rm -f -- "$sudo_rule"
echo 'Server configuration installed. Existing secrets, volumes, and release are preserved.'
