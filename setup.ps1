param(
    [switch]$RunMigrations,
    [switch]$RunTests
)

$venvPython = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    python -m venv .venv
}

& $venvPython -m pip install -r requirements.txt

if ($RunMigrations) {
    & $venvPython manage.py migrate
}

if ($RunTests) {
    & $venvPython manage.py test
}
