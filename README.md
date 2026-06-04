# Mittari

Observation statistics demo service.

Requirements:

- Local:
  - Docker or `uv`
- Deploying to OpenShift:
  - `oc`
  - `gh`

Note:

- Caching can be enabled/disabled in env var `CACHING_ON`. Visit /flush/{cache_secret} to flush the cache.

## Set up locally

Copy `.env.example` to `.env.local` (local development) and `.env.openshift` (production), and fill in values.

### Run locally with Docker Compose (recommended)

```bash
docker compose up --build
```

Then open: http://localhost:8080

### Run locally with uv (optional)

From the repo root, install dependencies into `.venv` and start Gunicorn with variables from `.env.local`:

```bash
uv sync
uv run --env-file .env.local -- sh -c 'gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers "${GUNICORN_WORKERS:-1}" --reload wsgi:app'
```

Then open: http://localhost:8080

### Run in production on OpenShift

1) Push to `main`. GitHub Actions builds and pushes the image to GHCR.

2) Wait for the workflow to finish: https://github.com/luomus/mittari/actions

3) Log in to OpenShift (command from the Rahti web UI) and select the project:

```bash
oc project mittari
```

4) Deploy the newest image (this also syncs `.env.openshift` to the cluster by default):

```bash
./scripts/deploy-openshift.sh
```

5) Verify rollout and running image:

```bash
oc rollout status deployment/mittari
oc get pods
oc get deployment mittari -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

The app is served at: https://mittari.2.rahtiapp.fi

## First-time setup

1) Select the OpenShift project:

```bash
oc project mittari
```

2) Create a GHCR pull secret (needed if the image is private):

```bash
oc create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-token-with-read-packages> \
  --docker-email=<email> \
  --dry-run=client -o yaml | oc apply -f -
```

Use a GitHub token with **`read:packages`**.

3) Create app resources from the template:

```bash
oc process -f openshift/mittari-app.yaml | oc apply -f -
```

4) Put production values in `.env.openshift`, then sync them to the cluster:

```bash
./scripts/sync-openshift-env.sh
```

5) After the first successful workflow run on `main`, point the deployment at a real image (the template starts from `ghcr.io/luomus/mittari:latest`):

```bash
./scripts/deploy-openshift.sh
```

6) Verify:

```bash
oc rollout status deployment/mittari
oc get pods
oc get route mittari
```

#### Update production env later

```bash
./scripts/deploy-openshift.sh
```
