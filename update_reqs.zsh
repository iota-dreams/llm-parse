#!/bin/zsh

set -e

# Dynamically activate conda/mamba environment (no hardcoded paths)
if command -v conda >/dev/null 2>&1; then
    # Source conda.sh to enable `conda activate`
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate llm_parse
elif command -v mamba >/dev/null 2>&1; then
    source "$(mamba info --base)/etc/profile.d/conda.sh"
    mamba activate llm_parse
else
    echo "⚠️ Neither conda nor mamba found; please activate environment manually."
fi

echo "🔄 Updating requirements files..."

mkdir -p deploy

echo "📁 Filtering valid source files (src/, app/, docs/)..."
TMP_DIR=$(mktemp -d /tmp/reqsfilter.XXXXXX)

for dir in src app docs; do
    if [[ -d "$dir" ]]; then
        rsync -av --include='*/' --include='*.py' --exclude='*' "$dir/" "$TMP_DIR/$dir/" >/dev/null
    fi
done

echo "📦 Generating deploy/requirements.txt from filtered source..."
pipreqs "$TMP_DIR" --force --savepath deploy/requirements.txt

# 🔧 Remove incorrect 'fitz' entry (alias for PyMuPDF)
sed -i.bak '/^fitz==/d' deploy/requirements.txt && rm deploy/requirements.txt.bak

# 📌 Append runtime-only packages with comment block
EXTRA_REQUIREMENTS_FILE="deploy/always_include.txt"

if [[ -f "$EXTRA_REQUIREMENTS_FILE" ]]; then
    {
        echo ""
        echo "# ---"
        echo "# The following packages are required for Docker/runtime"
        echo "# They are not directly imported in the source code, so pipreqs won't detect them"
        echo "# Maintained manually in deploy/always_include.txt"
        echo "# ---"
        cat "$EXTRA_REQUIREMENTS_FILE"
    } >> deploy/requirements.txt
    echo "📌 Appended always-include packages to requirements.txt"
else
    echo "⚠️ $EXTRA_REQUIREMENTS_FILE not found; skipping runtime-only packages"
fi

# (Optional) Create or ensure deploy/requirements_cloud.txt exists
if [[ ! -f deploy/requirements_cloud.txt ]]; then
    cat > deploy/requirements_cloud.txt <<EOF
google-cloud-logging==3.12.1
watchtower==3.4.0
opencensus-ext-azure==1.1.15
sentry-sdk==2.30.0
EOF
    echo "☁️ Created deploy/requirements_cloud.txt with cloud deps"
fi

echo "🧪 Generating deploy/requirements_dev.txt from environment..."
pip freeze > deploy/requirements_dev_raw.txt

# Replace commit hash (40 hex chars) in editable installs with branch name 'main'
sed -i.bak 's/@[0-9a-f]\{40\}/@main/g' deploy/requirements_dev_raw.txt
rm deploy/requirements_dev_raw.txt.bak

# Prepare deploy/requirements_dev.txt with references to base + cloud requirements
echo "-r requirements.txt" > deploy/requirements_dev.txt
echo "-r requirements_cloud.txt" >> deploy/requirements_dev.txt

# Gather base + cloud packages (package names only)
grep -v '^#' deploy/requirements.txt | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]' | sort | uniq > base_pkgs.txt
grep -v '^#' deploy/requirements_cloud.txt | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]' | sort | uniq > cloud_pkgs.txt

while read -r line; do
    pkg=$(echo "$line" | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]')
    if ! grep -qx "$pkg" base_pkgs.txt && ! grep -qx "$pkg" cloud_pkgs.txt; then
        echo "$line" >> deploy/requirements_dev.txt
    fi
done < deploy/requirements_dev_raw.txt

rm base_pkgs.txt cloud_pkgs.txt deploy/requirements_dev_raw.txt

# Cleanup
rm -rf "$TMP_DIR"

echo "✅ Requirements updated:"
echo " - deploy/requirements.txt"
echo " - deploy/requirements_cloud.txt"
echo " - deploy/requirements_dev.txt (with references)"
