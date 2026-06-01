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
  IMAGE_TAG="$(
    gh api "/orgs/${ORG}/packages/container/${PACKAGE}/versions" --paginate \
      --jq '[.[] | {created_at, tags: (.metadata.container.tags // [])}] |
            sort_by(.created_at) | reverse | .[] | .tags[] |
            select(test("^main-[0-9a-f]{7,}$"))' \
      | head -n 1
  )"
fi

if [ -z "${IMAGE_TAG}" ]; then
  echo "Could not find a deployable GHCR tag. Set IMAGE_TAG manually." >&2
  exit 1
fi

echo "Using image tag: ${IMAGE_TAG}"
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
