# Kubernetes Deployment Guide

This guide covers the basic operations for managing the Part Finder application in Kubernetes (k8s).

## Quick Start with Convenience Scripts

We've created scripts to make deployment easier:

### Local Development
```bash
./k8s/local-deploy.sh
```
This script automates the local development setup:
1. Loads environment variables from your `.env` file
2. Builds Docker images locally:
   - `part-finder-api:local`
   - `part-finder-web:local`
3. Sets up Kubernetes resources:
   - Creates the namespace
   - Applies ConfigMaps
   - Creates secrets from your environment variables
   - Sets up PostgreSQL with init scripts
4. Deploys all components using local images
5. Waits for all services to be ready
6. Provides the URL or port-forwarding instructions to access the application

Use this when developing on your local machine. Make sure you have a `.env` file with required variables:
- PINECONE_DB_API_KEY
- PINECONE_ENVIRONMENT
- MOUSER_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY

### Production Deployment
```bash
./k8s/deploy.sh
```
This script handles production deployment:
1. Creates the namespace
2. Applies ConfigMaps and secrets
3. Sets up PostgreSQL with init scripts
4. Deploys all components:
   - PostgreSQL database
   - API service
   - Web frontend
5. Waits for all services to be ready

The main differences from local deployment are:
- Uses production images instead of locally built ones
- Expects secrets to be pre-configured
- Designed for production environment setup

The benefit of these scripts is that they:
- Ensure consistent deployment steps
- Handle all the necessary Kubernetes resources
- Set up the correct environment variables
- Reduce the chance of mistakes
- Wait for services to be ready before completing

## Local Development Workflow Details

While `local-deploy.sh` handles the initial setup and basic updates, here's a breakdown of common tasks you might perform during local development:

### Applying Local Code Changes

When you modify the code (e.g., changing a Python file in the API or a Javascript file in the web frontend):

1.  **Run the deploy script:** This is the primary way to get your changes into the local cluster.
    ```bash
    ./k8s/local-deploy.sh
    ```
    This script should:
    *   Rebuild the relevant Docker image (e.g., `part-finder-web:local`) with your latest code.
    *   Apply the Kubernetes manifests (`k8s/*.yaml`), which *should* trigger an update if the deployment detects a change.

2.  **Force a Deployment Restart (If Necessary):** Sometimes, Kubernetes might not automatically roll out the changes, especially if you're using a static tag like `:local` for your images. If you run `local-deploy.sh` and don't see your changes reflected (after clearing browser cache for frontend changes), you can force the relevant deployment (e.g., `web` or `api`) to restart its pods:
    ```bash
    # Force restart for the web deployment
    kubectl rollout restart deployment/web -n part-finder

    # Force restart for the api deployment
    kubectl rollout restart deployment/api -n part-finder
    ```
    This command tells Kubernetes to terminate the existing pods and create new ones, ensuring they pull the latest version of the `*:local` image that `local-deploy.sh` just built.

### Checking Status

To see the state of your application components within the `part-finder` namespace:

*   **List all pods:** See if they are `Running`, `Pending`, `Error`, or `CrashLoopBackOff`.
    ```bash
    kubectl get pods -n part-finder
    ```
*   **List deployments:** Check if the desired number of replicas are available.
    ```bash
    kubectl get deployments -n part-finder
    ```
*   **List services:** See the internal cluster IPs and ports.
    ```bash
    kubectl get services -n part-finder
    ```
*   **Get detailed info on a specific pod:** Useful for troubleshooting pod startup issues.
    ```bash
    kubectl describe pod <pod-name> -n part-finder
    ```
    Replace `<pod-name>` with the actual name from `kubectl get pods`. Look at the `Events` section at the bottom for clues.

### Reading Logs

To view the real-time logs from a specific component:

*   **Web Frontend Logs:**
    ```bash
    # First find the web pod name
    kubectl get pods -n part-finder | grep web

    # Then stream its logs (replace <web-pod-name>)
    kubectl logs -f <web-pod-name> -n part-finder
    ```
*   **API Backend Logs:**
    ```bash
    # First find the api pod name
    kubectl get pods -n part-finder | grep api

    # Then stream its logs (replace <api-pod-name>)
    kubectl logs -f <api-pod-name> -n part-finder
    ```
*   **Database Logs:**
    ```bash
    # First find the postgres pod name
    kubectl get pods -n part-finder | grep postgres

    # Then stream its logs (replace <postgres-pod-name>)
    kubectl logs -f <postgres-pod-name> -n part-finder
    ```
    The `-f` flag follows the log output. Press `Ctrl+C` to stop streaming.

### Accessing the Web Frontend Locally

The `local-deploy.sh` script usually attempts to set up access. If not, or if you need to re-establish it, use port-forwarding:

```bash
kubectl port-forward service/web 3000:80 -n part-finder
```

Then access the application at `http://localhost:3000` in your browser. This command runs in the foreground, so you'll need to keep that terminal open or run it in the background.

### Stopping the Local Environment

To stop the application and remove all related Kubernetes resources:

1.  **Delete all resources defined in the k8s directory:**
    ```bash
    # Make sure you are in the project root or specify the correct path
    kubectl delete -f k8s/ -n part-finder
    ```
    This attempts to delete deployments, services, configmaps, secrets, etc., within the `part-finder` namespace based on your YAML files.

2.  **Delete the namespace (Optional but cleaner):** This removes the namespace itself and everything inside it.
    ```bash
    kubectl delete namespace part-finder
    ```

### Starting Over (Clean Slate)

If things get stuck or you want a completely fresh start:

1.  **Delete the namespace:** This ensures all previous resources are gone.
    ```bash
    kubectl delete namespace part-finder
    ```
    *(Wait a few moments for termination to complete)*
2.  **Run the local deployment script again:**
    ```bash
    ./k8s/local-deploy.sh
    ```
    This will recreate the namespace, rebuild images, and set everything up from scratch.

## What is Kubernetes?

Kubernetes is a container orchestration platform that helps manage containerized applications. Think of it as an automated system administrator that:
- Ensures your applications are always running
- Automatically recovers from failures
- Scales your applications up or down based on demand
- Manages network communication between different parts of your application

## Core Concepts

### Pods
A Pod is the smallest deployable unit in Kubernetes. Think of it as a wrapper around one or more containers. In our case:
- The web Pod contains your Flask application container
- The API Pod contains your Python backend container
- The PostgreSQL Pod contains your database container

### Services
Services provide a consistent way to access Pods. They act like a load balancer and ensure that requests reach the right Pods, even as Pods are created or destroyed. For example:
- The web service routes external traffic to your Flask application
- The API service ensures the web frontend can talk to the backend
- The PostgreSQL service allows the API to connect to the database

### Deployments
Deployments manage the lifecycle of Pods. They ensure:
- The specified number of Pods are always running
- Updates happen smoothly without downtime
- You can easily rollback to previous versions if something goes wrong

## Prerequisites

- kubectl installed and configured (this is the command-line tool for interacting with Kubernetes)
- Docker Desktop with Kubernetes enabled (for local development)
- Access to the part-finder namespace (namespaces are like folders that group related resources)

## Basic Commands

### Starting the Application

1. Apply all Kubernetes configurations:
```bash
kubectl apply -f k8s/
```

This command tells Kubernetes to create all the resources defined in your YAML files. It's like telling the system administrator to:
- Set up a new namespace for your application
- Start the database
- Launch the API server
- Start the web frontend
- Configure all the networking between them

### Stopping the Application

To stop all resources:
```bash
kubectl delete -f k8s/
```

This removes everything created by the apply command. Use this when you want to:
- Stop everything completely
- Free up resources
- Start fresh with a new configuration

### Checking Status

View all pods:
```bash
kubectl get pods -n part-finder
```
This shows you every running instance of your application components. You'll see:
- The name of each Pod
- Whether it's running or having problems
- How long it's been running
- How many times it's been restarted

View all services:
```bash
kubectl get services -n part-finder
```
This shows how your Pods are accessible:
- What IP addresses and ports are assigned
- Whether they're accessible from outside the cluster
- How they're named for internal communication

View all deployments:
```bash
kubectl get deployments -n part-finder
```
This shows the desired state of your application:
- How many copies of each component should be running
- How many are actually running
- Whether updates are in progress

### Making Changes

#### Code Changes
After making changes to the code:

1. Build and push the new Docker image:
```bash
docker build -t your-registry/part-finder-web:latest .
docker push your-registry/part-finder-web:latest
```
This packages your application code into a container image that Kubernetes can run.

2. Restart the deployment to pick up changes:
```bash
kubectl rollout restart deployment web -n part-finder
```
This tells Kubernetes to:
- Create new Pods with the updated image
- Wait for them to be ready
- Remove the old Pods
All of this happens without downtime!

#### Configuration Changes
When modifying Kubernetes configuration files:

1. Edit the YAML files in the k8s/ directory
2. Apply the changes:
```bash
kubectl apply -f k8s/modified-file.yaml
```
Kubernetes will automatically figure out what changed and make only the necessary updates.

### Debugging

View pod logs:
```bash
kubectl logs -f <pod-name> -n part-finder
```
This shows you what's happening inside your application:
- Application output (print statements, etc.)
- Error messages
- Request logs
The `-f` flag lets you "follow" the logs in real-time, like `tail -f`.

Execute commands in a pod:
```bash
kubectl exec -it <pod-name> -n part-finder -- /bin/bash
```
This lets you "get inside" a Pod to:
- Inspect the filesystem
- Run debugging commands
- Check configuration files
It's like SSH-ing into a server, but for containers.

View pod details:
```bash
kubectl describe pod <pod-name> -n part-finder
```
This gives you detailed information about a Pod:
- What node it's running on
- What container image it's using
- Recent events (crashes, restarts)
- Environment variables
- Volume mounts

### Common Issues and Solutions

1. **Pods not starting**
Problem: Your Pods are stuck in "Pending" or "CrashLoopBackOff" state
Solution: Check pod events
```bash
kubectl describe pod <pod-name> -n part-finder
```
This will show you:
- Why a Pod can't be scheduled
- Why containers are crashing
- Resource constraints
- Configuration problems

2. **Service not accessible**
Problem: You can't reach your application
Solution: Verify service configuration
```bash
kubectl get svc -n part-finder
kubectl describe svc <service-name> -n part-finder
```
This helps you check:
- If the service is properly configured
- What ports are being used
- If the service is finding the right Pods

3. **Database connection issues**
Problem: Your application can't connect to the database
Solution: Check environment variables and secrets
```bash
kubectl describe pod <postgres-pod-name> -n part-finder
```
Look for:
- Correct environment variables
- Mounted secrets
- Network policies that might block connections

## Best Practices

1. **Version Control**: Always keep your Kubernetes YAML files in version control
   - Track changes over time
   - Collaborate with team members
   - Roll back problematic changes

2. **Testing**: Test changes in development first
   - Use a local Kubernetes cluster
   - Verify all components work together
   - Check resource usage

3. **Resource Management**: Set appropriate limits
   - Prevent one application from using all resources
   - Ensure smooth scheduling
   - Plan capacity effectively

4. **Health Checks**: Implement proper probes
   - Liveness: Is your application alive?
   - Readiness: Is it ready to receive traffic?
   - Startup: Is it still starting up?

5. **Security**: Keep everything up to date
   - Update container images regularly
   - Apply security patches
   - Review access controls

## Need Help?

If you're stuck:
1. Check the logs first - they usually tell you what's wrong
2. Look at recent changes - did something just get updated?
3. Verify your configuration - are all the settings correct?
4. Check resource usage - are you running out of memory or CPU?
5. Review network connectivity - can all components talk to each other?

Remember: Kubernetes is complex, and it's okay to ask for help when needed!

## Architecture

The application consists of three main components:
- Web frontend (Flask application)
- API service (Python backend)
- PostgreSQL database

Each component runs in its own pod and communicates through Kubernetes services.

## Environment Variables

Important environment variables are configured in the deployment YAML files:
- `API_URL`: URL for the API service
- `DATABASE_URL`: PostgreSQL connection string
- Other configuration variables as needed

## Monitoring

To monitor application health:
```bash
kubectl get pods -n part-finder -w  # Watch pod status
kubectl top pods -n part-finder     # View resource usage
```

## Backup and Restore

### Database Backup
```bash
kubectl exec -it <postgres-pod-name> -n part-finder -- pg_dump -U postgres > backup.sql
```

### Database Restore
```bash
kubectl exec -it <postgres-pod-name> -n part-finder -- psql -U postgres < backup.sql
```

## Security

- Secrets are managed through Kubernetes secrets
- Network policies control pod-to-pod communication
- RBAC controls access to Kubernetes resources

## Troubleshooting

If you encounter issues:

1. Check pod logs
2. Verify configurations
3. Ensure all services are running
4. Check network connectivity
5. Verify resource availability

For more complex issues, refer to the Kubernetes documentation or contact the development team. 