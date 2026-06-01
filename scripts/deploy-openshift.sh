#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PROJECT="${PROJECT:-mittari}"
APP_NAME="${APP_NAME:-mittari}"
ORG="${ORG:-luomus}"
PACKAGE="${PACKAGE:-mittari}"
REGISTRY="${REGISTRY:-ghcr.io}"
SYNC_ENV_BEFORE_DEPLOY="${SYNC_ENV_BEFORE_DEPLOY:-1}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd oc
require_cmd gh

IMAGE_TAG="${IMAGE_TAG:-}"
if [ -z "${IMAGE_TAG}" ]; then
  if short_sha="$(git rev-parse --short=7 HEAD 2>/dev/null)"; then
    IMAGE_TAG="main-${short_sha}"
    echo "Using image tag from git HEAD: ${IMAGE_TAG}"
  fi
fi
if [ -z "${IMAGE_TAG}" ]; then
  IMAGE_TAG="$(
    gh api "/orgs/${ORG}/packages/container/${PACKAGE}/versions" --paginate \
      --jq '[.[] | select([.metadata.container.tags[]? | test("^main-[0-9a-f]{7,}$")] | any)] | if length == 0 then empty else (max_by(.updated_at // .created_at) | (.metadata.container.tags // []) | map(select(test("^main-[0-9a-f]{7,}$"))) | first // empty) end'
  )"
  if [ -n "${IMAGE_TAG}" ] && [ "${IMAGE_TAG}" != "null" ]; then
    echo "Using image tag from GHCR (no git repo): ${IMAGE_TAG}"
  fi
fi

if [ -z "${IMAGE_TAG}" ] || [ "${IMAGE_TAG}" = "null" ]; then
  echo "Could not determine image tag. Run from the mittari clone on the commit you pushed, or set IMAGE_TAG." >&2
  exit 1
fi

IMAGE="${REGISTRY}/${ORG}/${PACKAGE}:${IMAGE_TAG}"

echo "Using project: ${PROJECT}"
echo "Deploying image: ${IMAGE}"

if [ "${SYNC_ENV_BEFORE_DEPLOY}" = "1" ]; then
  echo "Syncing environment values from .env to OpenShift..."
  PROJECT="${PROJECT}" APP_NAME="${APP_NAME}" "${SCRIPT_DIR}/sync-openshift-env.sh"
fi

oc project "${PROJECT}" >/dev/null
oc set image "deployment/${APP_NAME}" "web=${IMAGE}"
oc rollout status "deployment/${APP_NAME}"

RUNNING_IMAGE="$(oc get deployment "${APP_NAME}" -o jsonpath='{.spec.template.spec.containers[0].image}')"
ROUTE_HOST="$(oc get route "${APP_NAME}" -o jsonpath='{.spec.host}')"

echo "Deployment updated successfully."
echo "Running image: ${RUNNING_IMAGE}"
echo "Route URL: https://${ROUTE_HOST}"
