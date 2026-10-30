# PinScout

An AI agent skill for browsing Pinterest, discovering visual inspiration, and downloading images and videos through a connected browser.

PinScout gives an agent a repeatable workflow for searching Pinterest, comparing references, opening the right pin, and delivering source links or local media files. It includes browser scripts and a Python downloader with no third-party runtime dependencies.

## What it does

- Collects rendered pins from search results or feeds and deduplicates them by pin ID.
- Helps an agent compare visual references and cite the original pin URLs.
- Extracts image variants and video formats for the current pin.
- Downloads the largest declared image variant or an available MP4 rendition.
- Checks media hosts, redirects, MIME types, file signatures, transfer sizes, and the configured size limit.
- Preserves existing files by adding a numeric suffix and reports the local path, byte count, MIME type, SHA-256, and source pin URL.

The published project is **PinScout**; its Agent Skill identifier remains **`pinterest`**, so existing prompts using `$pinterest` continue to work.

## Requirements

- An agent that can load `SKILL.md` instructions and control a browser.
- A browser connector that supports navigation and JavaScript evaluation. The initial workflow was tested with Chrome DevTools MCP connected to Microsoft Edge.
- A Pinterest session in that browser; sign in when Pinterest requires it.
- Python 3.10 or newer for the standalone downloader.

A browser extension is optional. PinScout can extract metadata and download media without one. It does not require a Pinterest developer API key.

## Installation

Clone this repository into a `pinterest` folder under your agent's supported skills directory.

For the Codex setup used during development:

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/humbertocortezia/pinscout-skill.git "${CODEX_HOME:-$HOME/.codex}/skills/pinterest"
```

Choose an empty destination; an existing manually installed `pinterest` skill needs to be backed up or updated separately. For another agent, use that agent's skill discovery directory and keep the repository contents together.

Start a new agent session or reload its skill catalog if it does not discover the new skill. The entry point is [SKILL.md](SKILL.md).

## Example prompts

```text
Use $pinterest to find five fitness landing page references.
Compare their layout, typography, and navigation, and include the pin URLs.
```

```text
Use $pinterest to download the image from this pin into ./references:
https://www.pinterest.com/pin/<pin-id>/
```

```text
Use $pinterest to download the video from this pin into ./videos.
If an MP4 is unavailable, tell me and keep the source link.
```

A research request does not automatically download files. Downloads, destinations, and quantities should follow the user's request.

## How downloads work

1. Open the exact pin in the connected browser.
2. Evaluate [scripts/read-pin.js](scripts/read-pin.js) on that page.
3. Save the returned metadata object as JSON, without tool wrappers or Markdown fences.
4. Run the helper with a destination:

```sh
python3 scripts/download.py --metadata /tmp/pin.json --kind image --output-dir ./references
python3 scripts/download.py --metadata /tmp/pin.json --kind video --output-dir ./videos
```

The default limit is 512 MiB per file. Override it explicitly when needed:

```sh
python3 scripts/download.py --metadata /tmp/pin.json --kind video --output-dir ./videos --max-mib 100
```

On success, the helper prints JSON:

```json
{
  "path": "/path/to/references/pinterest-123456789.jpg",
  "bytes": 125303,
  "mime": "image/jpeg",
  "sha256": "<sha256-of-the-downloaded-file>",
  "pinUrl": "https://www.pinterest.com/pin/123456789/",
  "pinId": "123456789"
}
```

This is an illustrative output, not a bundled download. Errors go to standard error as JSON and the process exits with a nonzero status.

Images retain a file extension matching the response type. Videos are saved as MP4. Existing files receive a suffix such as `-2`; failed partial transfers are removed. See [docs/metadata.md](docs/metadata.md) for the input schema.

### Browser scripts

Both JavaScript files contain a function to evaluate in a page. They are not Node.js programs or ES modules.

- [scripts/collect-pins.js](scripts/collect-pins.js): returns up to 50 currently rendered, deduplicated pins. Scroll incrementally and accumulate results because Pinterest virtualizes its grid.
- [scripts/read-pin.js](scripts/read-pin.js): matches the current pin ID against page data, falls back to a same-origin metadata request when necessary, and returns only the fields used for research and downloads.

With a compatible connector, use `sourcePath` with `format: "function"`. If the connector restricts local file paths, read the script through an authorized file tool and pass its source through the JavaScript evaluation tool's inline function field.

### Edge connection

For Windows and WSL, see [references/edge-connection.md](references/edge-connection.md). Reuse an existing working connection. A browser's debugging connection is separate from the downloaded files and does not require exporting session cookies.

## Limitations

- Pinterest's page structure and internal metadata endpoints can change.
- Not every video has a downloadable MP4. For HLS, the helper checks matching MP4 renditions on Pinterest's CDN; it does not join or transcode streaming segments.
- Embedded videos hosted by other websites are not handled.
- One execution downloads one image or one video; it does not export an entire carousel, board, or account.
- The largest declared image variant is not a guarantee of the creator's original resolution.
- A file signature check is not a full media decode. Verify playback or media tracks when that matters.
- Rate limits and access restrictions may prevent browsing or downloading.

## Privacy and scope

PinScout has no server or telemetry. The browser scripts use the connected session without returning cookies or the account's entire application state. The downloader accepts HTTPS media URLs only on `pinimg.com` and its subdomains, including after redirects.

Downloaded content retains its creator's rights. The skill does not grant rights to republish it. Publishing pins, modifying boards, following profiles, reacting, or sending messages are outside the research and download workflow unless separately requested.

## Validation

Run the offline downloader tests and JavaScript syntax checks:

```sh
python3 -m unittest discover -s tests -v
node --check scripts/collect-pins.js
node --check scripts/read-pin.js
```

The offline tests use synthetic responses and do not contact Pinterest. Initial live smoke checks also covered search results, image downloads, MP4 downloads from HLS metadata, and repeated downloads without overwriting. Those checks describe the observed behavior, not a guarantee for every pin.

## Contributing

For extraction failures, include the pin URL when shareable, the browser and connector used, the command, and the error message. Remove cookies, session tokens, and private account data from reports.
