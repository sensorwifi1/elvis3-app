@echo off
echo =======================================================
echo Deploying elvis3-app to Google Cloud Run
echo =======================================================
echo.

:: Ensure we are in the correct directory (c:\GIT\elvis3-app)
cd /d "%~dp0"
echo Current directory: %CD%

:: Deploying from the current directory ensures no parent wrap folder is sent
gcloud run deploy elvis3-app-v2 --source . --region europe-central2 --allow-unauthenticated

echo.
echo Deployment finished.
pause
