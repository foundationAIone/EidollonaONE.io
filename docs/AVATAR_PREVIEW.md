# Avatar Preview Workflow

Use these steps inside VS Code to validate and launch the avatar popup preview without touching external services.

## 1. Verify readiness

Run the task **Avatar: Check preview readiness**. It executes `scripts/avatar_preview_ready.py` and prints a PASS/WARN/FAIL matrix with the location of the generated JSON report. Address any WARN/FAIL items before proceeding.

## 2. Launch the preview

When the readiness check passes, run **Avatar: Run preview**. The PowerShell launcher will:

1. Resolve the interpreter (favoring the project virtual environment).
2. Ensure the preview requirements are installed.
3. Start `avatar_preview_server.py` in the background.
4. Open the popup webview in your default browser.

Use **Avatar: Check + Run** to chain the readiness probe and preview launch in one click.

## 3. Debug the backend server

To step through the FastAPI server, select the launch configuration **Python: avatar_preview_server.py** and press F5. The configuration reuses the same interpreter discovery logic as the tasks and launches the server under the debugger.

## 4. Troubleshooting tips

- Readiness warnings include quick remediation guidance; rerun the check after making fixes.
- If the browser does not open automatically, use the task output URL (`http://127.0.0.1:8000/static/webview/avatar_popup.html`).
- The readiness JSON report lives at `outputs/avatar_preview/report.json` by default; inspect it for detailed state.
- Stop the server by cancelling the terminal session started by the launcher or using the VS Code debug stop button.
