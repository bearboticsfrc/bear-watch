if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Please run as Administrator"
    exit 1
}

$pipList = python -m pip list --disable-pip-version-check *>&1 | Out-Null
if ($pipList -notmatch "asqlite" -or $pipList -notmatch "aiohttp") {
    python -m pip install -r requirements.txt
}

if (-not (Get-Command nmap -ErrorAction SilentlyContinue)) {
    Write-Host "nmap is not installed. Please install it from https://nmap.org/"
    exit 1
}

python .
