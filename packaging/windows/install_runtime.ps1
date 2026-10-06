param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference = 'Stop'
$signature = Get-AuthenticodeSignature -LiteralPath $Path
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '(^|,)\s*O=Microsoft Corporation(,|$)') {
    throw 'The Microsoft runtime download did not have a valid Microsoft signature.'
}
$p = Start-Process -FilePath $Path -Verb RunAs -ArgumentList '/install /quiet /norestart' -Wait -PassThru
if ($p.ExitCode -notin @(0,3010,1638)) { throw "Microsoft runtime installation failed ($($p.ExitCode)). Ask your computer administrator for help." }
