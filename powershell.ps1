# MyScript.ps1 (on Remote Server 1)

# Retrieve username and password from environment variables
$username = $env:USERNAME_ENV_VAR
$password = $env:PASSWORD_ENV_VAR | ConvertTo-SecureString -AsPlainText -Force

# Create a PSCredential object
$cred = New-Object System.Management.Automation.PSCredential ($username, $password)

# Define the path to the remote script on Server 2
$remoteScriptPath = "C:\Path\To\RemoteScript.ps1"

# Define the remote session to Server 2
$remoteSession = New-PSSession -ComputerName "RemoteServer2"

# Invoke the script on Remote Server 2 and pass the credential
Invoke-Command -Session $remoteSession -ScriptBlock {
    param($remoteScriptPath, $cred)
    & $remoteScriptPath -cred $cred
} -ArgumentList $remoteScriptPath, $cred

# Clean up the remote session to Server 2
Remove-PSSession -Session $remoteSession

# RemoteScript.ps1 (on Remote Server 2)

param(
    [Parameter(Mandatory=$true)]
    [System.Management.Automation.PSCredential]$cred
)

# Use the credential to make an HTTPS web request
$response = Invoke-WebRequest -Uri "https://example.com/api" -Credential $cred

# Output the response content
Write-Output $response.Content

