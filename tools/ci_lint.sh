#!/usr/bin/env bash
#
# Every static check CI runs: ruff, SCSS compiles, XML well-formed, the asset
# manifests, the Odoo 19/20 checklist, the brand-token and module-split rules, and
# the version bump.
#
#   tools/ci_lint.sh                  # everything that needs no base ref
#   BASE_REF=origin/20.0 tools/ci_lint.sh   # + the version-bump check
#
# .github/workflows/ci.yml calls this file rather than repeating the checks, so
# a runner, a laptop and a Claude cloud session cannot disagree about what
# "lint passes" means. Run it from anywhere; it cd's to the repo root.
set -uo pipefail

cd "$(dirname "$0")/.."

MODULES="pan_style_pro pan_style_pro_enterprise pan_style_pro_search"

FAILURES=0
step() { printf '\n=== %s\n' "$1"; }
fail() { echo "::error::$1"; FAILURES=$((FAILURES + 1)); }

# ---------------------------------------------------------------------------
step "Odoo series from the manifests"
python3 - $MODULES <<'PY' || fail "Could not read the version from a manifest."
import ast, sys
series = set()
for module in sys.argv[1:]:
    version = ast.literal_eval(open(f"{module}/__manifest__.py").read())["version"]
    parts = version.split(".")
    assert len(parts) == 5, f"{module}: version must be <series>.<x>.<y>.<z>.<w>, got {version!r}"
    series.add(".".join(parts[:2]))
    print(f"{module}: {version}")
assert len(series) == 1, f"modules disagree about the Odoo series: {series}"
print(f"Odoo {series.pop()}")
PY

# ---------------------------------------------------------------------------
step "ruff"
if command -v ruff >/dev/null 2>&1; then
    ruff check . || fail "ruff found problems."
else
    fail "ruff is not installed (pip install ruff==0.14.0)."
fi

# ---------------------------------------------------------------------------
# The theme is almost entirely SCSS, and Odoo compiles its bundles lazily on
# the first request — so a syntax error installs cleanly and only breaks the
# backend for the customer. Compiling every partial standalone is the check
# that install cannot give us.
step "SCSS compiles"
if command -v pysassc >/dev/null 2>&1; then
    while IFS= read -r file; do
        pysassc "$file" >/dev/null || fail "SCSS does not compile: $file"
    done < <(find $MODULES -name '*.scss' | sort)
    echo "OK: every partial compiles."
else
    fail "pysassc is not installed (pip install libsass==0.23.0)."
fi

# ---------------------------------------------------------------------------
step "XML is well-formed"
python3 - <<'PY' || fail "Malformed XML."
import os, sys
from xml.etree import ElementTree
failed = checked = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
    for name in files:
        if not name.endswith('.xml'):
            continue
        path = os.path.join(root, name)
        checked += 1
        try:
            ElementTree.parse(path)
        except ElementTree.ParseError as exc:
            print(f"::error file={path}::{exc}")
            failed += 1
print(f"Parsed {checked} XML file(s), {failed} malformed.")
sys.exit(1 if failed else 0)
PY

# ---------------------------------------------------------------------------
# A typo in an asset path is silent: Odoo logs a warning at bundle build time
# and serves the rest, so the styling is simply missing. The reverse is just as
# silent — a partial nobody registered is dead weight that looks live in the
# editor.
step "Asset and data paths match the manifests"
python3 - $MODULES <<'PY' || fail "Manifest and files disagree."
import ast, os, sys

modules = sys.argv[1:]
declared, missing, problems = set(), [], 0

def walk(entry):
    # Bundle entries are paths, or ("remove", path) / ("prepend", path) tuples.
    if isinstance(entry, str):
        return [entry]
    if isinstance(entry, (list, tuple)):
        return [e for e in entry if isinstance(e, str) and "/" in e]
    return []

for module in modules:
    manifest = ast.literal_eval(open(f"{module}/__manifest__.py").read())
    for bundle, entries in manifest.get("assets", {}).items():
        for entry in entries:
            for path in walk(entry):
                declared.add(path)
                if not os.path.exists(path):
                    missing.append(f"{module} [{bundle}] {path}")
    for path in manifest.get("data", []):
        if not os.path.exists(f"{module}/{path}"):
            missing.append(f"{module} [data] {path}")

for item in missing:
    print(f"::error::Declared but not on disk: {item}")
    problems += 1

# Only the file types that have to be registered to do anything. Fonts, images
# and Python are referenced from elsewhere.
for module in modules:
    for root, dirs, files in os.walk(f"{module}/static/src"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith((".scss", ".js", ".xml")):
                continue
            path = os.path.join(root, name)
            if path not in declared:
                print(f"::error file={path}::On disk but in no manifest bundle — dead asset.")
                problems += 1

print(f"{len(declared)} declared asset path(s), {problems} problem(s).")
sys.exit(1 if problems else 0)
PY

# ---------------------------------------------------------------------------
step "Odoo 19 — no attrs= in views"
if grep -rn 'attrs=' --include='*.xml' $MODULES; then
    fail "'attrs=' is removed in Odoo 17+. Use invisible/readonly/required directly."
else
    echo "OK: no attrs= found."
fi

step "Odoo 19 — no _sql_constraints assignment"
if grep -rn '^\s*_sql_constraints\s*=' --include='*.py' $MODULES; then
    fail "Odoo 19 ignores _sql_constraints and only warns, so the constraint is silently absent. Use models.Constraint."
else
    echo "OK: no _sql_constraints assignment found."
fi

# ---------------------------------------------------------------------------
# Odoo 20 runs OWL 3 and dropped Font Awesome and ir.config_parameter's
# get_param/set_param. Each of these installs cleanly and only breaks in the
# browser or on the first request, so install cannot catch them.
step "Odoo 20 — OWL 3, icons, config parameters"
ODOO20_OK=1
if grep -rnE '\b(useState|useRef)\b' --include='*.js' $MODULES; then
    fail "OWL 3 has no useState/useRef. Use proxy() and signal.ref()."; ODOO20_OK=0
fi
if grep -rnE 'static (props|defaultProps)\b' --include='*.js' $MODULES; then
    fail "OWL 3 throws on static props. Use 'props = useProps({...})'."; ODOO20_OK=0
fi
if grep -rn 't-esc=' --include='*.xml' $MODULES; then
    fail "t-esc is deprecated in OWL 3. Use t-out."; ODOO20_OK=0
fi
if grep -rnE '\bfa-[a-z]|class="fa |FontAwesome' --include='*.xml' --include='*.js' --include='*.scss' $MODULES; then
    fail "Font Awesome is not loaded in the Odoo 20 backend. Use <i class=\"oi\" data-icon=\"...\"/>."; ODOO20_OK=0
fi
if grep -rnE '\.(get|set)_param\b' --include='*.py' $MODULES; then
    fail "ir.config_parameter has no get_param/set_param in Odoo 20. Use get_str/set_str."; ODOO20_OK=0
fi
[ "$ODOO20_OK" = 1 ] && echo "OK: no OWL 2, Font Awesome or get_param leftovers."

# ---------------------------------------------------------------------------
# CLAUDE.md: OWL patches, no jQuery. A replaced component silently drops every
# other module's patch on it; jQuery is not loaded in the Odoo 19+ backend at
# all, so a `$(...)` call is a runtime error nothing here would otherwise see.
step "JS — no jQuery"
if grep -rn '\bjQuery\b\|[^A-Za-z_$.]\$(' --include='*.js' $MODULES; then
    fail "No jQuery in the Odoo 19+ backend — use vanilla JS or OWL."
else
    echo "OK: no jQuery."
fi

# ---------------------------------------------------------------------------
# CLAUDE.md: fonts are self-hosted. A CDN link is a third-party request on
# every backend page load, and it breaks on an air-gapped customer.
step "Fonts — no Google Fonts CDN"
if grep -rn 'fonts.googleapis.com\|fonts.gstatic.com' --include='*.scss' --include='*.xml' --include='*.js' $MODULES; then
    fail "Fonts must be self-hosted — no Google Fonts CDN."
else
    echo "OK: fonts self-hosted."
fi

# ---------------------------------------------------------------------------
# CLAUDE.md: brand values live in _tokens.scss only. A hex that leaks into a
# component partial is the one that gets missed when the brand changes, and it
# is invisible in dark mode until a customer reports it.
# A brand hex is allowed where a --pan-* token is being *defined* (that is
# what _tokens.scss does, and what _login.scss has to repeat because the
# frontend bundle does not load the backend tokens). Anywhere else it is a
# value that gets missed when the brand changes.
step "Brand — hardcoded brand hex only where a token is defined"
if grep -rniE '#(5b58d8|4a47c4|9b99ff|7370ff|001d21|002328|f4f5f7)' --include='*.scss' $MODULES \
   | grep -vE ':\s*--pan-[a-z0-9-]+:'; then
    fail "Brand colors belong in a --pan-* token definition — reference var(--pan-*) instead."
else
    echo "OK: brand hex only in token definitions."
fi

# The same accents in rgb() notation, the way tints used to be written
# (rgba(155, 153, 255, 0.1) is the dark accent leaking into light mode).
# Tints go through rgba(var(--pan-accent-rgb), x).
step "Brand — accent in rgb() only where --pan-accent-rgb is defined"
if grep -rnE 'rgba?\(\s*(91,\s*88,\s*216|155,\s*153,\s*255)' --include='*.scss' $MODULES; then
    fail "Accent rgb values belong in --pan-accent-rgb — use rgba(var(--pan-accent-rgb), x)."
else
    echo "OK: no hardcoded accent rgb."
fi

# ---------------------------------------------------------------------------
# CLAUDE.md module split: pan_style_pro stays Community-installable. A
# web_enterprise dependency there makes the module uninstallable on Community
# and the bridge module pointless.
step "Module split — pan_style_pro stays Community-compatible"
python3 - <<'PY' || fail "Module split violated."
import ast, sys
manifest = ast.literal_eval(open("pan_style_pro/__manifest__.py").read())
depends = manifest.get("depends", [])
bad = [d for d in depends if "enterprise" in d]
if bad:
    print(f"::error file=pan_style_pro/__manifest__.py::pan_style_pro may not depend on {bad} — use the bridge module.")
    sys.exit(1)
print(f"OK: pan_style_pro depends on {depends}.")
PY

# ---------------------------------------------------------------------------
step "Version bump"
if [ -n "${BASE_REF:-}" ]; then
    tools/ci_version_bump.sh "$BASE_REF" || fail "Version bump check failed."
else
    echo "BASE_REF not set — skipped (nothing to compare against)."
fi

# ---------------------------------------------------------------------------
printf '\n'
if [ "$FAILURES" -gt 0 ]; then
    echo "$FAILURES check(s) failed."
    exit 1
fi
echo "All static checks passed."
