#!/bin/bash

# Load environment variables from .env file
if [ -f ../.env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' ../.env | xargs)
else
    echo "Warning: .env file not found. Make sure all required environment variables are set."
fi

# Build local images
echo "Building local Docker images..."
cd ..  # Move to root directory
docker build -t part-finder-api:local -f Dockerfile.api .
docker build -t part-finder-web:local -f Dockerfile.web .
cd k8s  # Move back to k8s directory

# Create namespace
kubectl apply -f namespace.yaml

# Create ConfigMap for environment variables
kubectl apply -f configmap.yaml

# Create Secrets from .env file
echo "Creating secrets from environment variables..."
kubectl create secret generic part-finder-secrets \
  --from-literal=PINECONE_API_KEY="${PINECONE_DB_API_KEY}" \
  --from-literal=PINECONE_ENVIRONMENT="${PINECONE_ENVIRONMENT}" \
  --from-literal=MOUSER_API_KEY="${MOUSER_API_KEY}" \
  --from-literal=ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY}" \
  --from-literal=POSTGRES_PASSWORD="part_finder" \
  -n part-finder --dry-run=client -o yaml | kubectl apply -f -

# Create PostgreSQL ConfigMap for init script
kubectl create configmap postgres-init --from-file=../init.sql -n part-finder

# Deploy PostgreSQL
kubectl apply -f postgres.yaml

# Deploy API (using local image)
kubectl apply -f api-local.yaml

# Deploy Web (using local image)
kubectl apply -f web-local.yaml

# Wait for services to be ready
echo "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/postgres -n part-finder
kubectl wait --for=condition=available --timeout=300s deployment/api -n part-finder
kubectl wait --for=condition=available --timeout=300s deployment/web -n part-finder

# Get the web service URL
echo "Getting web service URL..."
WEB_URL=$(kubectl get service web -n part-finder -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$WEB_URL" ]; then
    WEB_URL=$(kubectl get service web -n part-finder -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
fi
if [ -z "$WEB_URL" ]; then
    echo "Could not get web service URL. You may need to use port-forwarding:"
    echo "kubectl port-forward service/web 3000:80 -n part-finder"
    echo "Then access the application at http://localhost:3000"
else
    echo "Application is available at http://${WEB_URL}"
fi

# Define Image URIs
export PROJECT_ID=bompartfinder
export REGION=us-central1 # Use the same region as your Artifact Registry repo
export REPO=part-finder-repo
export API_IMAGE_URI=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest
export WEB_IMAGE_URI=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/web:latest 