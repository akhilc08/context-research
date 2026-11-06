#!/usr/bin/env bash
# cloud-init user data for the benchmark validation host (Ubuntu 24.04).
# Installs Docker, Python 3.12, git, and pyarrow in the /opt/bench-venv virtualenv.
# Run the benchmark with /opt/bench-venv/bin/python. Safe to run more than once. No secrets.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git docker.io python3.12 python3.12-venv

python3.12 --version

# pyarrow comes from pip in a virtualenv, not from an apt package.
[ -x /opt/bench-venv/bin/python ] || python3.12 -m venv /opt/bench-venv
/opt/bench-venv/bin/pip install pyarrow

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
/opt/bench-venv/bin/python -c "import pyarrow; print('pyarrow', pyarrow.__version__)"
