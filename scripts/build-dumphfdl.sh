#!/bin/bash
# build-dumphfdl.sh — idempotent vendored build of libacars + dumphfdl
#
# Usage: sudo ./scripts/build-dumphfdl.sh [--force] [--no-apt]
#
# Builds libacars + dumphfdl from source into HFDL_RECORDER_PREFIX
# (default /opt/hfdl-recorder). Skips work that is already up to date.
#
# Honors these env vars:
#   HFDL_RECORDER_PREFIX     install prefix         (default: /opt/hfdl-recorder)
#   HFDL_RECORDER_BUILD_DIR  scratch build dir      (default: /var/cache/hfdl-recorder/build)
#   LIBACARS_REF             git ref for libacars   (default: master)
#   DUMPHFDL_REF             git ref for dumphfdl   (default: master)
#   LIBACARS_URL / DUMPHFDL_URL  override remotes
#
# After a successful run, ${PREFIX}/bin/dumphfdl is on disk and reports
# its --version cleanly when invoked via the linker rpath.

set -euo pipefail

PREFIX="${HFDL_RECORDER_PREFIX:-/opt/hfdl-recorder}"
BUILD_DIR="${HFDL_RECORDER_BUILD_DIR:-/var/cache/hfdl-recorder/build}"
LIBACARS_URL="${LIBACARS_URL:-https://github.com/szpajder/libacars.git}"
DUMPHFDL_URL="${DUMPHFDL_URL:-https://github.com/szpajder/dumphfdl.git}"
LIBACARS_REF="${LIBACARS_REF:-master}"
DUMPHFDL_REF="${DUMPHFDL_REF:-master}"

APT_DEPS=(
    build-essential cmake pkg-config git
    libxml2-dev libjansson-dev libsqlite3-dev libfftw3-dev
    libsoapysdr-dev libusb-1.0-0-dev zlib1g-dev
)

ui_info()  { echo "[INFO]  $*"; }
ui_warn()  { echo "[WARN]  $*" >&2; }
ui_error() { echo "[ERROR] $*" >&2; }

FORCE=false
SKIP_APT=false
for arg in "$@"; do
    case "$arg" in
        --force)  FORCE=true ;;
        --no-apt) SKIP_APT=true ;;
        *)        ui_warn "Ignoring unknown arg: $arg" ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    ui_error "Must run as root (sudo)"
    exit 1
fi

ensure_apt_deps() {
    if $SKIP_APT; then
        ui_info "Skipping apt deps (--no-apt)"
        return
    fi
    local missing=()
    for pkg in "${APT_DEPS[@]}"; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done
    if [[ ${#missing[@]} -eq 0 ]]; then
        ui_info "All apt build deps already present"
        return
    fi
    ui_info "Installing apt deps: ${missing[*]}"
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
}

clone_or_update() {
    local url="$1" ref="$2" dest="$3"
    if [[ ! -d "$dest/.git" ]]; then
        ui_info "Cloning $url -> $dest"
        git clone "$url" "$dest"
    else
        ui_info "Fetching $dest"
        git -C "$dest" fetch --tags --prune origin
    fi
    ui_info "Checking out $ref in $dest"
    git -C "$dest" checkout --quiet "$ref"
    # If ref is a branch name, fast-forward.
    if git -C "$dest" symbolic-ref -q HEAD >/dev/null; then
        git -C "$dest" pull --ff-only --quiet
    fi
}

build_one() {
    local name="$1" src="$2" extra_cmake_args="$3"
    local build="$src/build"
    local stamp="$build/.installed-rev"
    local current_rev
    current_rev=$(git -C "$src" rev-parse HEAD)

    if ! $FORCE && [[ -f "$stamp" ]] && [[ "$(cat "$stamp")" == "$current_rev" ]]; then
        ui_info "$name @ $current_rev already installed; skipping (use --force to rebuild)"
        return
    fi

    ui_info "Configuring $name (rev $current_rev)"
    rm -rf "$build"
    # shellcheck disable=SC2086
    cmake -S "$src" -B "$build" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$PREFIX" \
        -DCMAKE_INSTALL_LIBDIR=lib \
        -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
        -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        $extra_cmake_args >/dev/null

    ui_info "Building $name"
    cmake --build "$build" --parallel "$(nproc)" >/dev/null

    ui_info "Installing $name to $PREFIX"
    cmake --install "$build" >/dev/null

    echo "$current_rev" > "$stamp"
}

main() {
    ensure_apt_deps

    mkdir -p "$BUILD_DIR" "$PREFIX/bin" "$PREFIX/lib"

    local libacars_src="$BUILD_DIR/libacars"
    local dumphfdl_src="$BUILD_DIR/dumphfdl"

    clone_or_update "$LIBACARS_URL" "$LIBACARS_REF" "$libacars_src"
    build_one "libacars" "$libacars_src" ""

    clone_or_update "$DUMPHFDL_URL" "$DUMPHFDL_REF" "$dumphfdl_src"
    # PKG_CONFIG_PATH lets dumphfdl's CMake find our freshly installed libacars
    PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:${PKG_CONFIG_PATH:-}" \
        build_one "dumphfdl" "$dumphfdl_src" \
        "-DCMAKE_PREFIX_PATH=$PREFIX"

    # Bootstrap an empty systable.conf if dumphfdl ships one. dumphfdl will
    # extend it at runtime via --system-table-save as it learns ground stations.
    local shipped="$dumphfdl_src/etc/systable.conf"
    local installed="/var/lib/hfdl-recorder/systable.conf"
    if [[ -f "$shipped" ]] && [[ ! -f "$installed" ]]; then
        ui_info "Bootstrapping systable.conf -> $installed"
        mkdir -p "$(dirname "$installed")"
        cp "$shipped" "$installed"
    fi

    if ! "$PREFIX/bin/dumphfdl" --version >/dev/null 2>&1; then
        ui_error "dumphfdl built but failed --version sanity check"
        exit 1
    fi
    ui_info "Build complete. dumphfdl is at $PREFIX/bin/dumphfdl"
    "$PREFIX/bin/dumphfdl" --version 2>&1 | head -1 | sed 's/^/[INFO]  /'
}

main
