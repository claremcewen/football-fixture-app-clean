# Wrapper for the "She Can Kick It - Daily Fixtures" scheduled task.
# Pulls the latest fixture data before generating the digest, so it matches
# what the daily GitHub Action has already published - if the pull fails
# (e.g. no network yet at logon), carries on with whatever data is local.

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

git pull --ff-only 2>&1 | Out-Null

& "C:\Users\clare\AppData\Local\Programs\Python\Python313\pythonw.exe" "$RepoRoot\scripts\daily_digest.py"
