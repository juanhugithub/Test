param(
  [string]$Version = "v0.1.0"
)

$ErrorActionPreference = "Stop"

git tag $Version
git push origin $Version

Write-Host "Tag $Version pushed. GitHub Actions will create release artifacts automatically."
