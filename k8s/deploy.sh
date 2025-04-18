#!/bin/bash

# Create namespace
kubectl apply -f namespace.yaml

# Create ConfigMap for environment variables
kubectl apply -f configmap.yaml

# Create Secrets (make sure to replace the values with actual secrets)
kubectl apply -f secrets.yaml

# Create PostgreSQL ConfigMap for init script
kubectl create configmap postgres-init --from-file=init.sql -n part-finder

# Deploy PostgreSQL
kubectl apply -f postgres.yaml

# Deploy API
kubectl apply -f api.yaml

# Deploy Web
kubectl apply -f web.yaml

# Wait for services to be ready
echo "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/postgres -n part-finder
kubectl wait --for=condition=available --timeout=300s deployment/api -n part-finder
kubectl wait --for=condition=available --timeout=300s deployment/web -n part-finder

echo "Deployment complete!" 