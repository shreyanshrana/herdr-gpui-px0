#!/bin/sh
set -eu

version=${1:-0.1.0}
version=${version#v}
case "$version" in
    ''|*[!0-9.]*) echo "Expected a numeric release version" >&2; exit 1 ;;
esac
if ! grep -Fqx "version = \"$version\"" herdr-plugin.toml; then
    echo "Release version does not match herdr-plugin.toml" >&2
    exit 1
fi

name="herdr-px0_$version"
mkdir -p dist
git archive --format=tar.gz --prefix="$name/" HEAD \
    herdr-plugin.toml plugin.py README.md LICENSE CHANGELOG.md examples \
    > "dist/$name.tar.gz"
(cd dist && shasum -a 256 "$name.tar.gz" > SHA256SUMS)
