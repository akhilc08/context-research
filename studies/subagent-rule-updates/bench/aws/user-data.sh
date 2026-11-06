#!/usr/bin/env bash
# cloud-init user data for the benchmark validation host (Ubuntu 24.04).
# Installs Docker, Python 3.12, pip, pyarrow and git. Safe to run more than once. No secrets.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git docker.io python3.12 python3.12-venv python3-pip python3-pyarrow

python3.12 --version

systemctl enable --now docker

# SSM Session Manager sessions log in as ssm-user. The agent only creates it at the first
# session, so create it now; the agent reuses an existing ssm-user.
id ssm-user >/dev/null 2>&1 || useradd -m -s /bin/bash ssm-user
for account in ubuntu ssm-user; do
  if id "$account" >/dev/null 2>&1; then
    usermod -aG docker "$account"
  fi
done

docker --version
python3.12 -c "import pyarrow; print('pyarrow', pyarrow.__version__)"
