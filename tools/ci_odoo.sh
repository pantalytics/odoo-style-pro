#!/usr/bin/env bash
#
# Install the theme into a real Odoo of the matching series. Postgres included,
# everything runs in Docker, so it behaves the same on a GitHub runner, on a
# laptop and in a Claude cloud session.
#
#   tools/ci_odoo.sh                # install pan_style_pro on a fresh database
#   tools/ci_odoo.sh --mode=upgrade # install the last release, then upgrade to HEAD
#
# Env:
#   KEEP_DB=1      leave the Postgres container running afterwards
#   LOG_DIR=path   where to write the Odoo logs (default: repo root)
#
# pan_style_pro_enterprise is NOT installed here: it depends on web_enterprise,
# which is not in the community image. Its SCSS is compiled by tools/ci_lint.sh
# and its install stays a manual check on a real Enterprise database.
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
MODE=fresh
for arg in "$@"; do
    case "$arg" in
        --mode=*) MODE="${arg#--mode=}" ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done

LOG_DIR=${LOG_DIR:-$REPO}
mkdir -p "$LOG_DIR"

SERIES=$(python3 - "$REPO" <<'PY'
import ast, sys
manifest = ast.literal_eval(open(f"{sys.argv[1]}/pan_style_pro/__manifest__.py").read())
print(".".join(manifest["version"].split(".")[:2]))
PY
)
echo "Installing into Odoo ${SERIES} (mode: ${MODE})"

NET=pan_style_ci_net
DB=pan_style_ci_db

cleanup() {
    if [ -z "${KEEP_DB:-}" ]; then
        docker rm -f "$DB" >/dev/null 2>&1 || true
        docker network rm "$NET" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

docker rm -f "$DB" >/dev/null 2>&1 || true
docker network create "$NET" >/dev/null 2>&1 || true
docker run -d --name "$DB" --network "$NET" \
    -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres \
    postgres:15 >/dev/null

# Over TCP, not the unix socket: the image's entrypoint runs a temporary server
# with listen_addresses='' while it initialises, so a socket check answers
# "ready" to that one and the next command lands in the restart gap.
echo -n "Waiting for Postgres"
for _ in $(seq 1 60); do
    if docker exec "$DB" pg_isready -h localhost -U odoo >/dev/null 2>&1; then
        echo " ready."
        break
    fi
    echo -n "."
    sleep 1
done
docker exec "$DB" pg_isready -h localhost -U odoo >/dev/null

odoo_run() {
    # $1 = the repo root to mount as the addons directory, rest = odoo arguments
    local addons=$1
    shift
    docker run --rm --network "$NET" \
        -v "${addons}:/mnt/extra-addons:ro" \
        --entrypoint odoo "odoo:${SERIES}" \
        -d ci_style \
        --db_host="$DB" --db_port=5432 --db_user=odoo --db_password=odoo \
        --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons \
        --stop-after-init --max-cron-threads=0 "$@"
}

assert_installed() {
    # -i and -u on a module Odoo cannot find exit 0 without doing anything,
    # which is the exact failure this job would otherwise miss.
    local state
    state=$(docker run --rm --network "$NET" postgres:15 \
        psql "postgresql://odoo:odoo@${DB}:5432/ci_style" -tAc \
        "SELECT state FROM ir_module_module WHERE name = 'pan_style_pro'" | tr -d ' ')
    if [ "$state" != "installed" ]; then
        echo "::error::pan_style_pro is '${state:-absent}', not installed."
        exit 1
    fi
    echo "pan_style_pro is installed."
}

BASE_ADDONS=""
cleanup_all() {
    cleanup
    [ -n "$BASE_ADDONS" ] && rm -rf "$BASE_ADDONS"
    return 0
}
trap cleanup_all EXIT

if [ "$MODE" = "fresh" ]; then
    LOG="$LOG_DIR/odoo-install.log"
    set -o pipefail
    # --log-handler=odoo.tools.convert:DEBUG turns "Invalid view <name>
    # definition" with an empty context into a real traceback.
    odoo_run "$REPO" -i pan_style_pro --without-demo=all --log-level=info \
        --log-handler=odoo.tools.convert:DEBUG 2>&1 | tee "$LOG"
    assert_installed
    if grep -E '^[0-9-]+ [0-9:,]+ [0-9]+ (ERROR|CRITICAL)' "$LOG"; then
        echo "::error::Odoo logged an error while installing."
        exit 1
    fi
    echo "No errors in the install log."
    exit 0
fi

if [ "$MODE" != "upgrade" ]; then
    echo "unknown mode: $MODE (expected fresh or upgrade)" >&2
    exit 2
fi

# The customer path is an upgrade, not a fresh install: -u re-runs the data
# files and the post_init_hook against rows that already exist.
HEAD_SHA=$(git -C "$REPO" rev-parse HEAD)
TAG="${FROM_TAG:-}"
for t in $(git -C "$REPO" tag -l "v${SERIES}.*" --sort=-v:refname); do
    [ -n "$TAG" ] && break
    if [ "$(git -C "$REPO" rev-parse "${t}^{commit}")" != "$HEAD_SHA" ]; then
        TAG=$t
        break
    fi
done
if [ -z "$TAG" ]; then
    echo "No previous v${SERIES}.* tag — nothing to upgrade from."
    exit 0
fi
echo "Upgrading from ${TAG}"

BASE_ADDONS=$(mktemp -d)
git -C "$REPO" archive "$TAG" | tar -x -C "$BASE_ADDONS"
# mktemp gives 0700; the Odoo image runs as the unprivileged `odoo` user, which
# then reports the mount as an invalid addons directory.
chmod -R a+rX "$BASE_ADDONS"

set -o pipefail
odoo_run "$BASE_ADDONS" -i pan_style_pro --without-demo=all --log-level=warn 2>&1 \
    | tee "$LOG_DIR/odoo-baseline.log"
odoo_run "$REPO" -u pan_style_pro --log-level=info 2>&1 \
    | tee "$LOG_DIR/odoo-upgrade.log"
assert_installed
if grep -E '^[0-9-]+ [0-9:,]+ [0-9]+ (ERROR|CRITICAL)' "$LOG_DIR/odoo-upgrade.log"; then
    echo "::error::Odoo logged an error while upgrading."
    exit 1
fi
echo "No errors in the upgrade log."
