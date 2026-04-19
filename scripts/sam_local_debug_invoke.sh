#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <function_name> <port> <event_file> [--sync-fbplib] [--build-layer]"
  exit 1
fi

function_name="$1"
port="$2"
event_file="$3"
shift 3

sync_fbplib=false
build_layer=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sync-fbplib)
      sync_fbplib=true
      ;;
    --build-layer)
      build_layer=true
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
  shift
done

ids=$(docker ps -q --filter "publish=${port}")
if [[ -n "$ids" ]]; then
  docker rm -f $ids
fi

debugger_path=$(./.venv/bin/python -c "import site; print(site.getsitepackages()[0])")

if [[ "$sync_fbplib" == "true" ]]; then
  ./scripts/sync_fbplib_layer_requirements.sh
fi

if [[ "$build_layer" == "true" ]]; then
  sam build -t min.local.yaml FBPLibLayer
fi

sam build -t min.local.yaml "$function_name"

sam local invoke "$function_name" \
  -d "$port" \
  --debugger-path "$debugger_path" \
  --debug-args "-Xfrozen_modules=off -m debugpy --listen 0.0.0.0:${port} --wait-for-client" \
  -t .aws-sam/build/template.yaml \
  -e "$event_file"
