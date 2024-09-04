param(
    [Parameter(Mandatory=$true)]
    [pscredential]$Credential
)

# Extract username and password
$username = $Credential.UserName
$password = $Credential.GetNetworkCredential().Password

# Example HTTPS web request using the credentials
$response = Invoke-WebRequest -Uri "https://example.com/api" -Credential $Credential

# Output the response or process it as needed
Write-Output "Request completed with status: $($response.StatusCode)"


# Create a remote session to the remote machine
$session = New-PSSession -ComputerName "RemoteMachine"

# Prompt for credentials
$cred = Get-Credential

# Path to the script on the remote machine
$scriptPath = "C:\Path\To\MyScript.ps1"

# Invoke the remote script and pass the credentials
Invoke-Command -Session $session -ScriptBlock {
    param($scriptPath, $Credential)
    & $scriptPath -Credential $Credential
} -ArgumentList $scriptPath, $cred

# Clean up the session
Remove-PSSession -Session $session
