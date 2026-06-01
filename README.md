# Mittari

Observation statistics demo service.

Requirements:

- **Local:** [Docker](https://docs.docker.com/get-docker/)
- **Deploy to OpenShift:** [OpenShift CLI](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) (`oc`) and [GitHub CLI](https://cli.github.com/) (`gh`; the deploy script picks the newest `main-<sha>` image tag from GHCR)

## Set up locally

Create a `.env` file in the project root. Copy `.env.example` and fill in values.

### Run locally

```bash
docker compose up --build
```

Then open: http://localhost:8080

### Run in production on OpenShift

1) Push to `main`. GitHub Actions builds and pushes the image to GHCR.

2) Wait for the workflow to finish: https://github.com/luomus/mittari/actions

3) Log in to OpenShift (command from the Rahti web UI) and select the project:

```bash
oc project mittari
```

4) Deploy the newest image (this also syncs `.env` to the cluster by default):

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

4) Put production values in `.env`, then sync them to the cluster:

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
