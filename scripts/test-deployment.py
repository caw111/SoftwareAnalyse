#!/usr/bin/env python3
"""Bounded Linux deployment regression: temporary files and fake docker/curl only.

Run as root so deploy.sh's actual privilege check remains in force:
    sudo python3 scripts/test-deployment.py
The production script is read, never edited. No real container, database, registry
or network command is used. Only the copy's readonly deployment root is replaced.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

NEW_REVISION = "b" * 40
OLD_REVISION = "a" * 40
NEW_DIGEST = "sha256:" + "d" * 64
OLD_DIGEST = "sha256:" + "c" * 64
TOKEN = "fixture-only-registry-token-" + "x" * 48
DB_PASSWORD = "fixture-only-database-password"
ADMIN_PASSWORD = "fixture-only-administrator-password"

FAKE_COMMAND = r'''#!/usr/bin/python3
import json, os, pathlib, sys
args = sys.argv[1:]
command = pathlib.Path(sys.argv[0]).name
root = pathlib.Path(os.environ['FAKE_ROOT'])
release = root / 'release.env'
current = release.read_text() if release.exists() else ''
event = {'command': command, 'args': args, 'release': current}
with (root / 'calls.jsonl').open('a') as output:
    output.write(json.dumps(event) + '\n')
mode = os.environ['FAKE_SCENARIO']
new = os.environ['FAKE_NEW_DIGEST'] in current
if command == 'curl':
    url = args[-1]
    # Keep direct backend health separate from the explicitly verified TLS proxy.
    if url not in ('http://127.0.0.1:8081/actuator/health/readiness',
                   'http://127.0.0.1:18081/api/reference',
                   'https://49.233.93.248:8080/api/reference'):
        raise SystemExit('Unexpected health endpoint; refusing network access: ' + url)
    if url.startswith('https://'):
        for option, expected in (
                ('--noproxy', '*'),
                ('--cacert', str(root / 'tls' / 'server-ca.pem')),
                ('--connect-to', '49.233.93.248:8080:127.0.0.1:8080')):
            if option not in args or args[args.index(option) + 1] != expected:
                raise SystemExit('TLS probe must validate its CA and use the loopback proxy')
        if any(arg in ('-k', '--insecure') for arg in args):
            raise SystemExit('TLS verification cannot be disabled')
    if new and ((mode == 'readiness_failure' and url.endswith('/health/readiness'))
                or (mode == 'api_failure' and url == 'http://127.0.0.1:18081/api/reference')
                or (mode == 'proxy_failure' and url.startswith('https://'))):
        sys.exit(22)
    print('{"status":"UP"}')
    sys.exit(0)
if args[:1] == ['login']:
    credential = sys.stdin.read()
    if credential != os.environ['FAKE_TOKEN']:
        sys.exit(55)
    # Model a registry credential on disk so cleanup is a checked behavior.
    config = pathlib.Path(os.environ['DOCKER_CONFIG']) / 'config.json'
    config.write_text(json.dumps({'auths': {'ghcr.io': {'auth': credential}}}))
    sys.exit(0)
if args[:1] == ['pull']:
    if args[1] != 'ghcr.io/caw111/softwareanalyse-api@' + os.environ['FAKE_NEW_DIGEST']:
        sys.exit(56)
    sys.exit(0)
if args[:2] == ['image', 'inspect']:
    print('0' * 40 if mode == 'label_mismatch' else os.environ['FAKE_NEW_REVISION'])
    sys.exit(0)
if args[:1] == ['compose']:
    rest = args[1:]
    while rest and rest[0] in ('--env-file', '-f'):
        rest = rest[2:]
    if rest[:1] == ['up']:
        if rest[-1] == 'db':
            sys.exit(42 if mode == 'db_health_failure' else 0)
        sys.exit(43 if new and mode == 'health_failure' else 0)
    if rest[:1] == ['exec'] and 'pg_dump' in rest:
        if mode == 'backup_failure':
            print('mock backup failed', file=sys.stderr)
            sys.exit(44)
        print('MOCK-PG-DUMP')
        sys.exit(0)
raise SystemExit('Unsupported mock operation; refusing real execution: ' + command)
'''


def release_text(revision: str, digest: str) -> str:
    return f"API_IMAGE=ghcr.io/caw111/softwareanalyse-api@{digest}\nRELEASE_SHA={revision}\n"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_case(source: str, mode: str, existing: bool) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="academic-deploy-regression-") as directory:
        temporary = Path(directory)
        root, fakebin, home = temporary / "deployment", temporary / "bin", temporary / "home"
        for path in (root, fakebin, home):
            path.mkdir(mode=0o700)
        script = temporary / "deploy.sh"
        marker = "readonly root=/opt/academic-platform"
        require(source.count(marker) == 1, "Production root declaration changed; review harness before running")
        script.write_text(source.replace(marker, "readonly root=" + shlex.quote(str(root))), encoding="utf-8")
        for executable in ("docker", "curl"):
            target = fakebin / executable
            target.write_text(FAKE_COMMAND, encoding="utf-8")
            target.chmod(0o700)
        (root / "compose.yml").write_text("services: {}\n", encoding="utf-8")
        (root / "secrets.env").write_text(f"DB_PASSWORD={DB_PASSWORD}\nADMIN_PASSWORD={ADMIN_PASSWORD}\n", encoding="utf-8")
        previous = release_text(OLD_REVISION, OLD_DIGEST)
        if existing:
            (root / "release.env").write_text(previous, encoding="utf-8")
        environment = {
            "PATH": str(fakebin) + ":/usr/bin:/bin", "HOME": str(home), "LANG": "C.UTF-8",
            # A second guard: an accidentally invoked real CLI cannot reach Docker's socket.
            "DOCKER_HOST": "unix://" + str(temporary / "nonexistent-docker.sock"),
            "FAKE_ROOT": str(root), "FAKE_SCENARIO": mode, "FAKE_TOKEN": TOKEN,
            "FAKE_NEW_REVISION": NEW_REVISION, "FAKE_NEW_DIGEST": NEW_DIGEST,
        }
        result = subprocess.run(
            ["/bin/bash", str(script), NEW_REVISION, NEW_DIGEST],
            input=f"fixture-user\n{TOKEN}\n", text=True, capture_output=True,
            cwd=temporary, env=environment, timeout=20, check=False,
        )
        log = root / "deployments.log"
        eventlog = root / "calls.jsonl"
        transcript = result.stdout + result.stderr + (log.read_text() if log.exists() else "")
        transcript += eventlog.read_text() if eventlog.exists() else ""
        for secret in (TOKEN, DB_PASSWORD, ADMIN_PASSWORD):
            require(secret not in transcript, f"{mode}: credential leaked to output or audit/call logs")
        require(not list(root.glob(".registry-auth.*")), f"{mode}: registry credential directory was not removed")
        events = [json.loads(line) for line in eventlog.read_text().splitlines()] if eventlog.exists() else []
        main_updates = [event for event in events if event["command"] == "docker"
                        and event["args"][0] == "compose" and "up" in event["args"]
                        and event["args"][-1] != "db"]
        complete_backups = list((root / "backups").glob("*.dump"))
        health_urls = [event["args"][-1] for event in events if event["command"] == "curl"]
        expected_urls = ["http://127.0.0.1:8081/actuator/health/readiness",
                         "http://127.0.0.1:18081/api/reference",
                         "https://49.233.93.248:8080/api/reference"]
        require(set(health_urls).issubset(expected_urls), f"{mode}: probe used an unregistered endpoint")
        if mode == "success":
            require(result.returncode == 0, f"success: unexpected exit {result.returncode}")
            require(health_urls == expected_urls, "success: readiness, direct API and verified TLS proxy probes must all pass")
            require((root / "release.env").read_text() == release_text(NEW_REVISION, NEW_DIGEST), "success: release pointer was not advanced")
            require((root / "releases" / f"{NEW_REVISION}.env").is_file(), "success: verified release was not recorded")
            require(" success\n" in log.read_text(), "success: missing successful audit entry")
            require(len(complete_backups) == int(existing), "success: pre-upgrade backup count does not match deployment type")
        elif mode in ("health_failure", "readiness_failure", "api_failure", "proxy_failure"):
            require(result.returncode == 1, f"{mode}: failed deployment must report failure even after rollback")
            require((root / "release.env").read_text() == previous, f"{mode}: old release pointer was not restored")
            require(len(main_updates) == 2, f"{mode}: expected candidate activation and old-image rollback")
            attempted = {"health_failure": 0, "readiness_failure": 1, "api_failure": 2, "proxy_failure": 3}[mode]
            require(health_urls == expected_urls[:attempted] + expected_urls, f"{mode}: rollback did not repeat every health gate")
            require(NEW_DIGEST in main_updates[0]["release"] and OLD_DIGEST in main_updates[1]["release"], f"{mode}: rollback image order is wrong")
            require(" failed\n" in log.read_text(), f"{mode}: missing failure audit entry")
            require(not (root / "releases" / f"{NEW_REVISION}.env").exists(), f"{mode}: failed image recorded as verified")
        else:
            expected = {"backup_failure": 44, "label_mismatch": 65, "db_health_failure": 42}[mode]
            require(result.returncode == expected, f"{mode}: expected exit {expected}, got {result.returncode}")
            require((root / "release.env").read_text() == previous, f"{mode}: release changed before prerequisites passed")
            require(not main_updates, f"{mode}: application activation must not begin")
            require(not complete_backups, f"{mode}: failed/absent dump recorded as complete")
        return {"case": "initial_success" if not existing else "upgrade_" + mode,
                "exitCode": result.returncode, "passed": True,
                "credentialCleanup": True, "credentialLogsClean": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=Path(__file__).resolve().parents[1] / "deploy/server/deploy.sh")
    args = parser.parse_args()
    require(os.name == "posix" and os.geteuid() == 0, "Run on Linux as root; only temporary mock files are changed")
    source = args.script.read_text(encoding="utf-8")
    require("/usr/bin/docker" not in source and "/usr/bin/curl" not in source, "Absolute executable paths require a new mock safety review")
    results = [run_case(source, "success", False)]
    for scenario in ("success", "health_failure", "readiness_failure", "api_failure", "proxy_failure", "backup_failure", "label_mismatch", "db_health_failure"):
        results.append(run_case(source, scenario, True))
    print(json.dumps({"mockOnly": True, "realDockerInvoked": False, "cases": results}, indent=2))


if __name__ == "__main__":
    main()
