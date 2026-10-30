# Connect to Microsoft Edge from Windows or WSL

Read this only when the browser connector cannot connect. Check the current connector configuration rather than copying a historical IP address or recreating a working connection. Avoid printing configuration files that may contain secrets.

## Diagnose the endpoint

1. List tabs through the connector.
2. If that fails, identify the configured endpoint and the browser's actual debugging port. One supported arrangement uses Windows loopback port `9222`, forwarded to port `9223` on the Windows host address reachable from WSL. These are example ports, not mandatory constants.
3. Check the Windows side in PowerShell:
   ```powershell
   Invoke-RestMethod http://127.0.0.1:9222/json/version
   Get-NetTCPConnection -State Listen -LocalPort 9222,9223 -ErrorAction SilentlyContinue
   netsh interface portproxy show all
   ```
   There is no need to include the browser WebSocket endpoint in the user-facing report.
4. If Windows succeeds while WSL fails, inspect the host address, forwarding rule, and firewall. A stale IPv4-to-IPv6 rule targeting the wrong port can reset connections even when Edge is running.

## Open a dedicated session

When debugging is not already enabled, have the user run this in Windows PowerShell, or launch it yourself when authorized by the current task:

```powershell
& "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\Edge-Codex" "https://www.pinterest.com/"
```

Adjust the executable path when Edge is installed elsewhere. Reuse the dedicated profile to preserve its login; the user signs into that window. Do not terminate unrelated browser windows to force debugging.

## Windows-to-WSL forwarding

Discover the current Windows host address, such as WSL's default gateway in NAT mode. With mirrored networking, localhost may already work; test that before adding a forwarding rule.

When needed, a scoped IPv4 rule has this form in an administrator PowerShell:

```powershell
netsh interface portproxy add v4tov4 listenaddress=<Windows-host-IP> listenport=9223 connectaddress=127.0.0.1 connectport=9222
```

Use the specific address reachable from WSL rather than exposing debugging on every interface. Inspect a conflicting rule before replacing it and explain the change. Do not disable the firewall or add broad exceptions. UAC or additional permissions follow the authorization rules of the current session; preserve unrelated rules.

Test `/json/version` at the connector endpoint, then list tabs again. If the connector points to an old endpoint, update only that configuration when authorized. A running connector may need to reload before using its changed configuration.

## Connector limitations and downloads

Some connectors block `chrome-extension:` URLs or browser-internal pages. Prefer normal page controls and supported tools. If a required operation is unavailable, direct CDP can be used within the same authorized scope; ordinary research does not require installing or reloading extensions.

Automation can redirect downloads to an Edge temporary directory. Check the completed download's actual path before promising a default Downloads folder. Copy completed files to the requested destination without overwriting existing files when necessary.

Protocol documentation: [Microsoft Edge DevTools Protocol](https://learn.microsoft.com/en-us/microsoft-edge/devtools/protocol/).
