#!/usr/bin/env bash
#
# The whole of CI, locally: static checks, a fresh install, and the upgrade
# from the last release. This is what .github/workflows/ci.yml runs on a push,
# in the same order, calling the same scripts.
#
#   tools/ci.sh              # everything
#   tools/ci.sh lint         # static checks only (seconds)
#   tools/ci.sh install      # install pan_style_pro into a real Odoo
#   tools/ci.sh upgrade      # install the last release, then upgrade to HEAD
#
# lint needs ruff and libsass (pip install ruff==0.14.0 libsass==0.23.0).
# install and upgrade need Docker and network access to Docker Hub.
set -euo pipefail
cd "$(dirname "$0")/.."

WHAT=${1:-all}
case "$WHAT" in
    lint)    tools/ci_lint.sh ;;
    install) tools/ci_odoo.sh --mode=fresh ;;
    upgrade) tools/ci_odoo.sh --mode=upgrade ;;
    all)
        tools/ci_lint.sh
        tools/ci_odoo.sh --mode=fresh
        tools/ci_odoo.sh --mode=upgrade
        ;;
    *) echo "usage: tools/ci.sh [all|lint|install|upgrade]" >&2; exit 2 ;;
esac
