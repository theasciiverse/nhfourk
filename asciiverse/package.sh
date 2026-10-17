#!/bin/sh
# Packs the game into its archive for av: release/<id>-<target>.tar.gz
# (.zip for Windows), from the list in asciiverse/archive/<id>.txt: one
# file per line, relative to the repo root, all placed side by side at the
# top of the archive; "src -> name" renames. Binaries listed as out/<name>
# get .exe on Windows. (Not dist/, as in the other Asciiverse repos:
# upstream keeps its icons and Debian packaging there.)
#
#   asciiverse/package.sh x86_64-unknown-linux-musl
set -eu
cd "$(dirname "$0")/.."
target="$1"
case "$target" in *windows*) exe=.exe ;; *) exe= ;; esac
mkdir -p release
for list in asciiverse/archive/*.txt; do
  id=$(basename "$list" .txt)
  stage="out/stage/$id"
  rm -rf "$stage" && mkdir -p "$stage"
  grep -v '^#' "$list" | while read -r src arrow name; do
    [ -n "$src" ] || continue
    case "$src" in out/*) [ -f "$src$exe" ] && src="$src$exe" ;; esac
    if [ "$arrow" = "->" ]; then cp "$src" "$stage/$name"; else cp "$src" "$stage/"; fi
  done
  if [ -n "$exe" ]; then
    (cd "$stage" && zip -qr "../../../release/$id-$target.zip" .)
  else
    tar -czf "release/$id-$target.tar.gz" -C "$stage" .
  fi
done
ls release
