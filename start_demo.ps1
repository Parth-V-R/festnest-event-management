param(
    [switch]$SkipMinio
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing Python dependencies..."
& $venvPython -m pip install -r requirements.txt

Write-Host "Running database migrations..."
& $venvPython manage.py migrate

if (-not $SkipMinio) {
    $composeFile = "deploy\minio\compose.yml"
    $minioEnvExample = "deploy\minio\.env.example"
    $minioEnv = "deploy\minio\.env"

    if (Test-Path $composeFile) {
        if (-not (Test-Path $minioEnv) -and (Test-Path $minioEnvExample)) {
            Copy-Item -LiteralPath $minioEnvExample -Destination $minioEnv -Force
        }

        $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
        if ($dockerCmd) {
            Write-Host "Starting MinIO via Docker Compose..."
            try {
                docker compose -f $composeFile --env-file $minioEnv up -d
            } catch {
                docker-compose -f $composeFile --env-file $minioEnv up -d
            }
            Write-Host "MinIO console (if started): http://127.0.0.1:9001"
        } else {
            Write-Host "Docker not found. Skipping MinIO startup."
        }
    }
}

Write-Host "Starting FestNest at http://127.0.0.1:8000 ..."
& $venvPython manage.py runserver
