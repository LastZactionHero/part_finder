# PCB Part Finder Deployment Guide

This guide will help you deploy the PCB Part Finder application to a production environment.

## Prerequisites

1. A VPS (Virtual Private Server) running Ubuntu 20.04 or later
2. A domain name (e.g., pcbpartfinder.com)
3. SSH access to your VPS
4. Docker and Docker Compose installed on your local machine
5. API keys for Mouser and Anthropic

## Quick Start

1. **Prepare your VPS:**
   - Purchase a VPS from a provider like DigitalOcean, Linode, or AWS
   - Note down the IP address
   - Set up SSH access

2. **Configure DNS:**
   - Point your domain to your VPS IP address
   - Add both the root domain and www subdomain
   - Wait for DNS propagation (can take up to 24 hours)

3. **Deploy the application:**
   ```bash
   # Run the setup script
   ./setup.sh yourdomain.com your.vps.ip.address
   
   # Review and update the .env.production file with your API keys
   nano deploy/config/.env.production
   
   # Copy files to the VPS
   scp -r deploy/* root@your.vps.ip.address:/opt/part_finder/
   
   # SSH into the VPS and run the deployment script
   ssh root@your.vps.ip.address
   cd /opt/part_finder
   ./scripts/deploy.sh
   ```

## Production Configuration

The deployment script sets up:

1. **Docker Environment:**
   - Docker and Docker Compose
   - Container networking
   - Volume mounts for persistent data

2. **Web Server (Nginx):**
   - SSL/TLS encryption
   - Reverse proxy configuration
   - Automatic SSL renewal

3. **Security:**
   - Environment variable management
   - Secure SSL configuration
   - System updates

4. **Monitoring:**
   - Docker container logging
   - System resource monitoring

## Maintenance

### Updating the Application

To update the application:

1. Pull the latest changes
2. Rebuild and restart the containers:
   ```bash
   cd /opt/part_finder
   docker-compose -f deploy/config/docker-compose.prod.yml down
   docker-compose -f deploy/config/docker-compose.prod.yml up -d --build
   ```

### Backing Up Data

The application data is stored in:
- `/opt/part_finder/projects/` - Project files
- `/opt/part_finder/cache/` - Cache data

Regular backups are recommended. You can use the following command to create a backup:
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz /opt/part_finder/projects /opt/part_finder/cache
```

### Monitoring

The application includes:
- Docker container logs
- Nginx access and error logs
- System resource monitoring

To view logs:
```bash
# View container logs
docker-compose -f deploy/config/docker-compose.prod.yml logs

# View Nginx logs
docker-compose -f deploy/config/docker-compose.prod.yml logs nginx
```

## Troubleshooting

Common issues and solutions:

1. **SSL Certificate Issues:**
   - Check DNS propagation
   - Verify domain points to correct IP
   - Check certbot logs: `journalctl -u certbot`

2. **Container Issues:**
   - Check container logs
   - Verify environment variables
   - Check network connectivity

3. **Performance Issues:**
   - Monitor system resources
   - Check container resource limits
   - Review application logs

## Security Considerations

1. Keep the system updated:
   ```bash
   apt-get update && apt-get upgrade -y
   ```

2. Use strong passwords and API keys
3. Regularly backup your data
4. Monitor for security updates
5. Use a firewall (UFW recommended):
   ```bash
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 22/tcp
   ufw enable
   ``` 