# Sanitize.ps1 — Strip secrets from files before committing
param(
    [string]$Path = "."
)

$patterns = @(
    @{ Find = 'sk-[a-zA-Z0-9]{20,}'; Replace = 'sk-REDACTED' }
    @{ Find = 'ghp_[a-zA-Z0-9]{36}'; Replace = 'ghp_REDACTED' }
    @{ Find = 'gho_[a-zA-Z0-9]{36}'; Replace = 'gho_REDACTED' }
    @{ Find = 'Bearer [a-zA-Z0-9\.\-_]{20,}'; Replace = 'Bearer REDACTED' }
    @{ Find = '"token"\s*:\s*"[^"]+"'; Replace = '"token": "REDACTED"' }
    @{ Find = '"password"\s*:\s*"[^"]+"'; Replace = '"password": "REDACTED"' }
    @{ Find = '"apiKey"\s*:\s*"[^"]+"'; Replace = '"apiKey": "REDACTED"' }
    @{ Find = '"api_key"\s*:\s*"[^"]+"'; Replace = '"api_key": "REDACTED"' }
)

$extensions = @("*.json", "*.yaml", "*.yml", "*.ini", "*.cfg", "*.conf", "*.txt", "*.md", "*.ps1", "*.py")

$files = Get-ChildItem -Path $Path -Recurse -Include $extensions -File

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }

    $changed = $false
    foreach ($p in $patterns) {
        if ($content -match $p.Find) {
            $content = $content -replace $p.Find, $p.Replace
            $changed = $true
        }
    }

    if ($changed) {
        $content | Set-Content $file.FullName -NoNewline -Encoding utf8
        Write-Host "  Sanitized: $($file.FullName)"
    }
}
