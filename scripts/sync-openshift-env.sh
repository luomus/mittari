#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-mittari}"
APP_NAME="${APP_NAME:-mittari}"
ENV_FILE="${ENV_FILE:-.env.openshift}"
SECRET_NAME="${SECRET_NAME:-${APP_NAME}-env-secret}"

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

declare -a secret_args

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

  if [ -z "${key}" ]; then
    continue
  fi

  # Strip one matching pair of surrounding double quotes (dotenv-style), so values match Docker/uv.
  if [[ "${value}" == \"*\" ]] && [[ "${value}" != "\"" ]]; then
    value="${value#\"}"
    value="${value%\"}"
  fi

  secret_args+=(--from-literal="${key}=${value}")
done < "${ENV_FILE}"

oc project "${PROJECT}" >/dev/null

if [ ${#secret_args[@]} -eq 0 ]; then
  echo "No environment entries found in ${ENV_FILE}; skipping secret update." >&2
  exit 1
fi

oc create secret generic "${SECRET_NAME}" \
  "${secret_args[@]}" \
  --dry-run=client -o yaml | oc apply -f -

echo "Synced OpenShift env from ${ENV_FILE}"
echo "Secret: ${SECRET_NAME}"
