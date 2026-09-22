#!/bin/sh

set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/.." && pwd)

"$script_directory/build.sh"
exec "$repository_root/bin/aiutils" --root "$repository_root" claude-to-codex "$@"
