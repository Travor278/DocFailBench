param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PipArgs
)

if (-not $PipArgs -or $PipArgs.Count -eq 0) {
    Write-Error "Usage: scripts\pip_direct.ps1 install <package> [pip args...]"
    exit 2
}

$proxyNames = @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy"
)

$saved = @{}
foreach ($name in $proxyNames) {
    $item = Get-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    if ($item) {
        $saved[$name] = $item.Value
        Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    }
}

try {
    & python -m pip @PipArgs
    exit $LASTEXITCODE
}
finally {
    foreach ($name in $saved.Keys) {
        Set-Item -LiteralPath "Env:$name" -Value $saved[$name]
    }
}
