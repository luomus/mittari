#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-mittari}"
APP_NAME="${APP_NAME:-mittari}"
ENV_FILE="${ENV_FILE:-.env}"
SECRET_NAME="${SECRET_NAME:-${APP_NAME}-env-secret}"
CONFIGMAP_NAME="${CONFIGMAP_NAME:-${APP_NAME}-env-config}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd oc

if [ ! -f "${ENV_FILE}" ]; then
  echo "Env file not found: ${ENV_FILE}" >&2
  exit 1
fi

declare -a secret_keys
declare -a config_keys
declare -a secret_args
declare -a config_args

secret_keys=(
  "LAJI_API_ACCESS_TOKEN"
  "SECRET_KEY"
  "FLUSH_SECRET_KEY"
)

config_keys=(
  "PORT"
  "GUNICORN_WORKERS"
)

is_in_list() {
  local needle="$1"
  shift
  local candidate
  for candidate in "$@"; do
    if [ "${candidate}" = "${needle}" ]; then
      return 0
    fi
  done
  return 1
}

while IFS= read -r raw_line || [ -n "${raw_line}" ]; do
  line="${raw_line#"${raw_line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  if [ -z "${line}" ] || [[ "${line}" == \#* ]]; then
    continue
  fi

  if [[ "${line}" == export\ * ]]; then
    line="${line#export }"
  fi

  if [[ "${line}" != *=* ]]; then
    continue
  fi

  key="${line%%=*}"
  value="${line#*=}"
  key="${key%"${key##*[![:space:]]}"}"
  key="${key#"${key%%[![:space:]]*}"}"

  if is_in_list "${key}" "${secret_keys[@]}"; then
    secret_args+=(--from-literal="${key}=${value}")
    continue
  fi

  if is_in_list "${key}" "${config_keys[@]}"; then
    config_args+=(--from-literal="${key}=${value}")
  fi
done < "${ENV_FILE}"

oc project "${PROJECT}" >/dev/null

if [ ${#secret_args[@]} -gt 0 ]; then
  oc create secret generic "${SECRET_NAME}" \
    "${secret_args[@]}" \
    --dry-run=client -o yaml | oc apply -f -
else
  echo "No secret keys found in ${ENV_FILE}; skipping secret update."
fi

if [ ${#config_args[@]} -gt 0 ]; then
  oc create configmap "${CONFIGMAP_NAME}" \
    "${config_args[@]}" \
    --dry-run=client -o yaml | oc apply -f -
else
  echo "No config keys found in ${ENV_FILE}; skipping configmap update."
fi

echo "Synced OpenShift env from ${ENV_FILE}"
echo "Secret: ${SECRET_NAME}"
echo "ConfigMap: ${CONFIGMAP_NAME}"
