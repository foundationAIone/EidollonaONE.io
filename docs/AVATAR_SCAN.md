# Avatar Assets Scan

Quick steps to run the avatar asset inventory tooling.

## Run from VS Code

- Open **Build → Run Task…** and choose **Avatar: Scan assets**.
- A new terminal appears, runs the scan, and prints the latest `logs/avatar_assets_scan_*.json` path plus the first ~60 lines.

## Run from shell

```powershell
pwsh -File scripts/run_avatar_scan.ps1 -Repo E:\EidollonaONE -Top 12
```

- Works from any PowerShell prompt (adjust `-Repo` / `-Top` as needed).

## Output

- JSON report saved to `logs/avatar_assets_scan_*.json`.
- The runner prints the report path and a preview of the first lines to the terminal for quick inspection.
