# Reproducing Windows validation

Build the installer using [the Windows guide](../packaging/windows/README.md). Test the resulting artifact in actual Windows 10 and Windows 11 x64 installations; run source tests on Linux separately. Download official evaluation media from Microsoft if using a lab, and comply with its evaluation terms. Do not attach Windows images, VM disks or test credentials to application releases.

The 1.2.0 lab used KVM/QEMU with UEFI, TPM 2.0, Microsoft evaluation images and a local test account. Windows 11 had 4 virtual CPUs/4 GB RAM; Windows 10 had 2 virtual CPUs/3 GB RAM. These constrained lab allocations are not the operator recommendation (8 GB RAM). The Linux host's production church service and recording jobs were left running and were not used as test fixtures.

## First installation and real inference

Start with a clean Windows OS. Install with the wizard, open the desktop shortcut, approve the Microsoft C++ prerequisite if prompted and allow first setup to finish. Inspect the setup log and dependency notices. Reopen the shortcut and check that it reconnects. The church logo should be visible in the interface.

Generate an English synthetic speech fixture, or use a synthetic fixture you are authorized to share. For example, PowerShell can use the Windows speech synthesizer:

```powershell
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
$wav = "$env:TEMP\ccs-test-speech.wav"
$speech.SetOutputToWaveFile($wav)
$speech.Speak('Welcome to Christ Church Southampton. Today we are reading from Romans chapter two, verses one to sixteen. God judges fairly. Let us pray together.')
$speech.Dispose()
$env:CCS_TEST_SPEECH = $wav
$app = "$env:LOCALAPPDATA\Programs\CCSVideoCleanup"
& "$app\runtime\python.exe" "$app\app\windows\launcher.py" --module windows.verify
```

The recorded 1.2.0 test used espeak-ng British English, generated on Linux and copied into the isolated lab. The verifier runs real RapidOCR, loads the cached speech model with `local_files_only=True`, transcribes the fixture and renders an opposed-stereo synthetic video in a temporary path containing spaces and non-ASCII characters. It checks chapters, mono audio, the intro, HTTP logo/health/jobs endpoints, repeat setup, duplicate launch and active-processing shutdown refusal. Reports and synthetic output are under `%LOCALAPPDATA%\CCSVideoCleanup\verification`.

## Source regression tests

Copy this repository's `tests` directory into a test folder. From PowerShell, use the installed launcher so tests see the private dependencies:

```powershell
$app = "$env:LOCALAPPDATA\Programs\CCSVideoCleanup"
Set-Location "$app\app"
& "$app\runtime\python.exe" "$app\app\windows\launcher.py" --module unittest discover -s 'C:\CCS-tests\tests' -v
foreach ($name in 'download_access', 'preview_display', 'progress_display', 'review_precision') {
    & "$env:LOCALAPPDATA\CCSVideoCleanup\tools\deno.exe" run --allow-read "C:\CCS-tests\tests\$name.js"
}
```

Keep PowerShell's error preference at its normal `Continue` while capturing native test output: unittest writes progress to stderr, which Windows PowerShell 5.1 can wrap as `NativeCommandError` even when the suite succeeds. Check the process exit code and `OK`, not that wrapper label alone. The packaged Windows HTML defaults to anonymous download access; the source UI's Firefox default remains for Linux.

## Installer and retention checks

Create a synthetic data sentinel. Hold the actual `ccs.common.LOCK` using `ccs.locking.file_lock` in a second process and keep it held until both attempted update and uninstall have returned. Both must leave the application/data and running server intact. Release the lock, update, open the real desktop shortcut, uninstall while idle, and verify that the application/runtime were removed while the sentinel, synthetic finished video, cached models and setup record remain. Reinstall and check that setup is reused.

NSIS uninstall copies itself to a temporary child process. Inspect the application/server and retained files when checking refusal; the original parent exit code alone does not establish the child result. Avoid launching interactive wizards from a background lab session: the window may belong to a different Windows session from the console. Launch the wizard directly from the visible desktop to inspect and click it.

Finally, test a fresh private library directory and a data path containing spaces/non-ASCII characters. Upstream download/model caches can be copied into that isolated folder to avoid redundant network traffic, but there must be no successful setup marker or private Python packages before that check. Never perform these destructive test resets in an operator's real data folder.

## Network limits and release record

Try the downloader against an authorized public service URL without repeatedly retrying rate limits. The 1.2.0 lab's live YouTube metadata request returned HTTP 429/sign-in verification; a successful authenticated Windows download was not claimed. Firefox-cookie instructions remain available to operators. No personal browser cookies or accounts were copied into the lab.

Record the exact installer hash/byte size, OS builds, test output and limits in [the release validation record](validation/v1.2.0.md). Keep screenshots and inference fixtures synthetic or deidentified. Preserve prior release artifacts unchanged.
