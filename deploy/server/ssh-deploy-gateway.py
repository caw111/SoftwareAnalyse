#!/usr/bin/python3
"""Forced SSH command: no shell, files, port forwarding, or arbitrary image names."""
import os
import re
import sys

match = re.fullmatch(r"deploy ([0-9a-f]{40}) (sha256:[0-9a-f]{64})", os.environ.get("SSH_ORIGINAL_COMMAND", ""))
if not match:
    sys.exit("Only a deployment of one commit and immutable image digest is permitted.")
os.execv("/usr/bin/sudo", ["sudo", "-n", "/usr/local/sbin/academic-deploy", *match.groups()])
