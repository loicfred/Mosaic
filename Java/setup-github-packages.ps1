# One-time setup so Maven can download SolarFramework from GitHub Packages.
# Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File Java\setup-github-packages.ps1
# It asks for a GitHub classic token with read:packages, checks it, saves it as the user variables
# GITHUB_ACTOR/GITHUB_TOKEN and adds the "github" server to ~/.m2/settings.xml. The token is never written to a file.

$ErrorActionPreference = 'Stop'
$TokenPage = 'https://github.com/settings/tokens/new?scopes=read:packages&description=SolarFramework%20Maven'
$ParentPom = 'https://maven.pkg.github.com/solarflare-mu/solarframework/org/solarframework/mu/solar-framework/1.0/solar-framework-1.0.pom'
$SettingsFile = Join-Path $env:USERPROFILE '.m2\settings.xml'

function Read-Token {
    Write-Host "Create a token here (tick only read:packages), then copy it:"
    Write-Host "  $TokenPage"
    Start-Process $TokenPage
    $secure = Read-Host 'Paste the token' -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    return $plain.Trim()
}

function Get-GitHubLogin([string]$token) {
    $headers = @{ Authorization = "Bearer $token"; 'User-Agent' = 'solarframework-setup' }
    try {
        return (Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers).login
    } catch {
        throw 'GitHub refused this token. Copy it again, or create a new one.'
    }
}

function Test-PackageAccess([string]$login, [string]$token) {
    $pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${login}:$token"))
    try {
        Invoke-WebRequest -Uri $ParentPom -Headers @{ Authorization = "Basic $pair" } -UseBasicParsing | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Add-GitHubServer {
    if (-not (Test-Path $SettingsFile)) {
        New-Item -ItemType Directory -Force (Split-Path $SettingsFile) | Out-Null
        Set-Content -Path $SettingsFile -Encoding UTF8 -Value '<settings>
  <servers>
  </servers>
</settings>'
    }
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($SettingsFile)
    $ns = $doc.DocumentElement.NamespaceURI
    $existing = $doc.DocumentElement.ChildNodes | Where-Object { $_.LocalName -eq 'servers' } |
        ForEach-Object { $_.ChildNodes } | Where-Object { $_.LocalName -eq 'server' -and $_.id -eq 'github' }
    if ($existing) {
        Write-Host "settings.xml already has the github server."
        return
    }
    $servers = $doc.DocumentElement.ChildNodes | Where-Object { $_.LocalName -eq 'servers' } | Select-Object -First 1
    if (-not $servers) {
        $servers = $doc.DocumentElement.AppendChild($doc.CreateElement('servers', $ns))
    }
    $server = $servers.AppendChild($doc.CreateElement('server', $ns))
    foreach ($field in @(@('id', 'github'), @('username', '${env.GITHUB_ACTOR}'), @('password', '${env.GITHUB_TOKEN}'))) {
        $node = $server.AppendChild($doc.CreateElement($field[0], $ns))
        $node.InnerText = $field[1]
    }
    $doc.Save($SettingsFile)
    Write-Host "Added the github server to $SettingsFile"
}

$token = Read-Token
$login = Get-GitHubLogin $token
Write-Host "Token belongs to $login."
if (-not (Test-PackageAccess $login $token)) {
    throw 'The token works but cannot download SolarFramework. Make sure read:packages is ticked.'
}
[Environment]::SetEnvironmentVariable('GITHUB_ACTOR', $login, 'User')
[Environment]::SetEnvironmentVariable('GITHUB_TOKEN', $token, 'User')
Add-GitHubServer
Write-Host ''
Write-Host 'Done. Quit IntelliJ completely (File > Exit), start it again, then Reload All Maven Projects.'
