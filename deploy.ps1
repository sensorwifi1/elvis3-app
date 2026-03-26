# Deployment Script for elvis3-app
# This script ensures that gcloud deploys from the actual folder
# so that the root of the repo is correctly placed in /workspace.

Write-Host "======================================================="
Write-Host "Deploying elvis3-app to Google Cloud Run"
Write-Host "======================================================="

# Ensure working directory is the script directory
Set-Location -Path $PSScriptRoot
Write-Host "Current directory: $(Get-Location)"

# Deploy from the current directory
gcloud run deploy elvis3-app-v2 --source . --region europe-central2 --allow-unauthenticated

Write-Host "`nDeployment finished."
Pause
