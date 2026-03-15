# GitHub Actions Setup Guide

## Prerequisites
- A GitHub repository with this code pushed
- Docker Hub account with username `saji7x`
- EC2 instance running with Docker (IP: 13.51.42.73)
- SSH key-pair (`newsdigest.pem`)

## Required GitHub Secrets

Go to your GitHub repository → **Settings → Secrets and variables → Actions** and add these secrets:

### 1. Docker Hub Credentials

**`DOCKER_USERNAME`**
- Value: `saji7x`
- Purpose: Docker Hub username for pushing images

**`DOCKER_PASSWORD`**
- Value: Your Docker Hub **Personal Access Token (PAT)** with read/write permissions
- How to create:
  1. Go to https://app.docker.com/settings/personal-access-tokens
  2. Click **Create new token**
  3. Name: `GitHub Actions`
  4. Select **Read & Write** scope
  5. Copy the token and paste it here (NOT your password)

### 2. AWS EC2 Credentials

**`EC2_HOST`**
- Value: `13.51.42.73`
- Purpose: Public IP of your EC2 instance

**`EC2_SSH_KEY`**
- Value: Full content of your `newsdigest.pem` private key file
- How to get:
  ```powershell
  Get-Content "C:\Users\SajimithanPathmanath\Downloads\newsdigest.pem" | Set-Clipboard
  # Then paste into the GitHub secret
  ```
- ⚠️ **Important**: Make sure to include the entire key including:
  ```
  -----BEGIN RSA PRIVATE KEY-----
  ...key content...
  -----END RSA PRIVATE KEY-----
  ```

### 3. Application Secrets

**`GROQ_API_KEY`**
- Value: Your GROQ API key (e.g., `gsk_...`)
- Purpose: LLM API access for the application
- Location in code: Used by backend services

## Automated Deployment Workflow

### How it works:

```
1. You push code to main branch
   ↓
2. GitHub Actions triggers docker-build.yml
   → Builds backend Docker image
   → Builds frontend Docker image
   → Pushes both to Docker Hub
   ↓
3. GitHub Actions triggers docker-deploy.yml
   → SSHes into EC2
   → Pulls latest images from Docker Hub
   → Stops old containers
   → Starts new containers
   → Runs health checks
```

### Triggering deployments:

Push changes to main branch:
```bash
git add .
git commit -m "feat: update application"
git push origin main
```

Monitor the workflow:
- Go to **GitHub → Actions tab**
- Click the latest workflow run
- Watch build and deployment progress

## Testing Deployments

### Manual test (after secrets are configured):

1. Make a small change to backend code:
   ```python
   # backend/app/main.py
   # Add a comment or modify a string
   ```

2. Commit and push:
   ```bash
   git add backend/
   git commit -m "test: verify auto-deployment"
   git push origin main
   ```

3. Watch the GitHub Actions workflow
4. Once complete, visit http://13.51.42.73 to verify the new version is running

### Checking deployment status on EC2:

```bash
# SSH into EC2
ssh -i C:\Users\SajimithanPathmanath\Downloads\newsdigest.pem ubuntu@13.51.42.73

# View running containers
docker compose ps

# View logs
docker compose logs -f backend  # Backend logs
docker compose logs -f frontend # Frontend logs

# Check health
curl http://localhost:8000/health
curl http://localhost/
```

## Troubleshooting

### If deployment fails:

1. **Check GitHub Actions logs**
   - Go to Actions tab → Latest run → Click job name
   - Look for error messages

2. **Common issues**:
   - ❌ "Permission denied (publickey)" → EC2_SSH_KEY not set correctly
   - ❌ "unauthorized: incorrect username or password" → DOCKER_PASSWORD is incorrect PAT
   - ❌ "Cannot pull image" → DOCKER_USERNAME mismatch
   - ❌ "Connection refused" → EC2 instance not running

3. **Manual troubleshooting**:
   ```bash
   # SSH to EC2 and check manually
   ssh -i newsdigest.pem ubuntu@13.51.42.73
   docker compose logs backend | tail -20
   docker ps
   ```

## Next Steps

- ✅ Configure all GitHub secrets
- ✅ Make a test push to verify CI/CD works
- ⬜ Set up SSL certificate with Certbot
- ⬜ Set up custom domain
- ⬜ Configure monitoring/alerts

## Quick Reference

| Secret | Example Value |
|--------|---------------|
| DOCKER_USERNAME | saji7x |
| DOCKER_PASSWORD | dckr_pat_abc123xyz... |
| EC2_HOST | 13.51.42.73 |
| EC2_SSH_KEY | -----BEGIN RSA PRIVATE KEY-----\n...key content...\n-----END RSA PRIVATE KEY----- |
| GROQ_API_KEY | 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 |
