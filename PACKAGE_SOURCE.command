#!/bin/bash
# Crea un ZIP limpio del código fuente necesario para construir QA Tools localmente.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

APP_VERSION="$(sed -nE 's/^APP_VERSION = "([^"]+)"/\1/p' app_metadata.py)"
if [[ -z "$APP_VERSION" ]]; then
    echo "No se pudo obtener APP_VERSION desde app_metadata.py." >&2
    exit 1
fi

PACKAGE_NAME="QA_Tools_${APP_VERSION}_Source"
OUTPUT_DIR="$PROJECT_DIR/dist"
ARCHIVE_PATH="$OUTPUT_DIR/${PACKAGE_NAME}.zip"
STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/qa-tools-source.XXXXXX")"
PACKAGE_DIR="$STAGING_DIR/$PACKAGE_NAME"

cleanup() {
    rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

copy_clean_tree() {
    local source="$1"
    local destination="$2"
    local item relative target

    while IFS= read -r -d '' item; do
        relative="${item#"$source"}"
        relative="${relative#/}"
        target="$destination/$relative"
        if [[ -d "$item" ]]; then
            mkdir -p "$target"
        else
            mkdir -p "$(dirname "$target")"
            cp -p "$item" "$target"
        fi
    done < <(
        find "$source" \
            \( -name '.DS_Store' -o -name '__pycache__' -o -name '.pytest_cache' \) -prune \
            -o -print0
    )
}

mkdir -p "$PACKAGE_DIR"

# Los módulos y tests son necesarios para que BUILD_QA_TOOLS.command valide el proyecto.
find "$PROJECT_DIR" -maxdepth 1 -type f -name '*.py' -exec cp {} "$PACKAGE_DIR" \;
cp "$PROJECT_DIR/requirements.txt" "$PROJECT_DIR/QA Tools.spec" "$PROJECT_DIR/README.md" "$PACKAGE_DIR"
ditto "$PROJECT_DIR/BUILD_QA_TOOLS.command" "$PACKAGE_DIR/BUILD_QA_TOOLS.command"

if [[ -d "$PROJECT_DIR/templates" ]]; then
    copy_clean_tree "$PROJECT_DIR/templates" "$PACKAGE_DIR/templates"
fi
if [[ -d "$PROJECT_DIR/tests" ]]; then
    copy_clean_tree "$PROJECT_DIR/tests" "$PACKAGE_DIR/tests"
fi
if [[ -d "$PROJECT_DIR/assets" ]]; then
    copy_clean_tree "$PROJECT_DIR/assets" "$PACKAGE_DIR/assets"
fi

mkdir -p "$OUTPUT_DIR"
rm -f "$ARCHIVE_PATH"
(
    cd "$STAGING_DIR"
    COPYFILE_DISABLE=1 /usr/bin/zip -qry "$ARCHIVE_PATH" "$PACKAGE_NAME"
)

echo "========================================"
echo "PAQUETE FUENTE CREADO"
echo "========================================"
echo "$ARCHIVE_PATH"
echo
echo "Incluye código Python, templates, tests, requirements.txt, QA Tools.spec,"
echo "README.md y BUILD_QA_TOOLS.command."
echo "No incluye .git, .venv, build, dist, cachés, logs ni archivos temporales."
