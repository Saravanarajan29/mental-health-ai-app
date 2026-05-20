$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

Write-Host "Starting Mental Health AI app..."
Write-Host "Project: $projectRoot"
Write-Host "URL: http://127.0.0.1:8501"

python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
