param(
    [switch]$SkipSeed,
    [switch]$Insecure
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$collection = Join-Path $root "docs\postman\retiro-escolar-seguro-a-b.postman_collection.json"
$environment = Join-Path $root "docs\postman\retiro-escolar-seguro-a-b.postman_environment.json"

Set-Location $root

docker compose up -d --build app
docker compose exec app python manage.py check

if (-not $SkipSeed) {
    docker compose exec app python scripts/seed_demo.py
}

$newman = Get-Command newman -ErrorAction SilentlyContinue
if ($null -eq $newman) {
    $newman = Get-Command npx -ErrorAction SilentlyContinue
    if ($null -eq $newman) {
        throw "Instala Node.js/Newman o ejecuta manualmente la colección desde Postman."
    }
    $runner = @("npx", "--yes", "newman", "run", $collection, "-e", $environment)
} else {
    $runner = @("newman", "run", $collection, "-e", $environment)
}

if ($Insecure) {
    $runner += "--insecure"
}

& $runner[0] $runner[1..($runner.Count - 1)]
if ($LASTEXITCODE -ne 0) {
    throw "La colección Postman terminó con errores."
}
