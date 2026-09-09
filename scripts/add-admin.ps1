param(
    [Parameter(Position = 0)]
    [string]$Email = $env:ADMIN_EMAIL,
    [Parameter(Position = 1)]
    [string]$Password = $env:ADMIN_PASSWORD
)

if (-not $Email -or -not $Password) {
    Write-Error "Usage: .\scripts\add-admin.ps1 <email> <password>"
    exit 1
}

docker compose --profile tools run --rm `
    -e "ADMIN_EMAIL=$Email" `
    -e "ADMIN_PASSWORD=$Password" `
    create-admin
