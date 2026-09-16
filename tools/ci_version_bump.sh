#!/usr/bin/env bash
#
# Odoo hosts decide whether to run an upgrade by comparing the manifest version
# to the installed one. A theme change that ships without a bump is simply
# never applied on the customer's database — the old CSS keeps being served.
#
#   tools/ci_version_bump.sh <base-ref>     # e.g. origin/19.0
#
# Checked per module: only the module you touched needs the bump.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE_REF=${1:?usage: ci_version_bump.sh <base-ref>}

# Compares against the merge base rather than the PR's base SHA, so this also
# runs on a plain branch push — before a PR exists, which is when the bump is
# easiest to forget.
if ! MERGE_BASE=$(git merge-base "$BASE_REF" HEAD 2>/dev/null); then
    echo "::error::No merge base with $BASE_REF; cannot check the version bump."
    exit 1
fi
echo "Comparing against $BASE_REF at $MERGE_BASE"

python3 - "$MERGE_BASE" <<'PY'
import ast, subprocess, sys

base = sys.argv[1]
MODULES = ["pan_style_pro", "pan_style_pro_enterprise"]

def version(text):
    return tuple(int(p) for p in ast.literal_eval(text)["version"].split("."))

def show(ref, path):
    out = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None

changed = subprocess.run(
    ["git", "diff", "--name-only", base, "HEAD"],
    capture_output=True, text=True, check=True).stdout.split()

failed = False
for module in MODULES:
    touched = [f for f in changed
               if f.startswith(f"{module}/") and not f.endswith((".md", ".txt"))]
    if not touched:
        print(f"{module}: untouched — no bump required.")
        continue
    old_text = show(base, f"{module}/__manifest__.py")
    if old_text is None:
        print(f"{module}: new module — no previous version to compare.")
        continue
    new, old = version(open(f"{module}/__manifest__.py").read()), version(old_text)
    if new <= old:
        print(f"::error file={module}/__manifest__.py::{module} changed but version was not bumped "
              f"({'.'.join(map(str, old))} -> {'.'.join(map(str, new))}). "
              f"Odoo skips the upgrade without a higher version.")
        failed = True
    else:
        print(f"{module}: bumped {'.'.join(map(str, old))} -> {'.'.join(map(str, new))}")

sys.exit(1 if failed else 0)
PY
