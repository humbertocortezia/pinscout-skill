---
name: pinterest
description: Browse and search Pinterest, compare visual references, and download images and videos from pins through a connected browser. Use for Pinterest research, curation, design inspiration, and media downloads; not for publishing pins or managing ads.
---

# PinScout

Use the user's connected browser session to find pins, inspect their content, and deliver links or files according to the request. Research does not imply downloading. Saving a pin to a board is different from downloading a file.

## Connect and research

- Discover the available browser tools and list existing tabs before opening another. Prefer the current connector. Chrome DevTools MCP can also control Microsoft Edge.
- If it cannot connect, read [references/edge-connection.md](references/edge-connection.md).
- Preserve the authenticated session; let the user sign in when needed. Do not export cookies or read credential files.
- Search through the interface or open `https://www.pinterest.com/search/pins/?q=<encoded-query>`. Preserve the session's Pinterest domain when possible.
- Evaluate [scripts/collect-pins.js](scripts/collect-pins.js) to collect rendered pins. With compatible tools, use `sourcePath` and `format: "function"`; the file is a function, not a module.
- Some connectors restrict `sourcePath` to configured workspace roots. Read the script through an authorized file tool and pass its source inline, or use a copy inside the authorized workspace.
- Scroll incrementally and collect again. Pinterest's virtualized grid may remove earlier cards from the DOM. Accumulate results and deduplicate by `pinId`. Stop when the requested material is sufficient; report blocking or rate limits instead of retrying indefinitely.
- Open selected candidates. Thumbnails, titles, and descriptions are clues: inspect the pin before describing details or choosing downloads. Cite each pin URL. Distinguish the profile that pinned an item from its original creator when authorship is unverified.

For design references, compare observable composition, hierarchy, typography, palette, density, and interaction patterns. Select for the user's request and briefly explain what makes each reference useful.

## Download images and videos

Open the exact pin before extracting media. Match the URL's pin ID to the metadata; recommendations and stale scripts from an earlier navigation are not the current pin's content.

**With the optional Pinterest Leve extension:** if present, click the main pin's **Baixar vídeo** button inside `[data-pl-control="closeup"]`. Feed controls are separate. Check the browser's completed download; “Download iniciado” only means it started. Respect the user's extension toggle setting. Do not install an extension merely to perform research.

**Without that extension, or for images:**

1. Evaluate [scripts/read-pin.js](scripts/read-pin.js) on the pin page. It returns the required metadata, including image variants and video formats, rather than the account's entire application state.
2. Save the returned object to a temporary JSON file, without Markdown fences or tool text envelopes.
3. Run the helper with the requested media kind and destination:
   ```sh
   python3 <skill-dir>/scripts/download.py --metadata /tmp/pin.json --kind image --output-dir <destination>
   python3 <skill-dir>/scripts/download.py --metadata /tmp/pin.json --kind video --output-dir <destination>
   ```
   Resolve `<skill-dir>` from this skill's location. If no destination was specified, choose a clear folder within the current project and report its path.
4. Check the final JSON fields: `path`, `bytes`, `mime`, `sha256`, and `pinUrl`. Inspect downloaded images when appearance matters. For video, verify playback or at least media tracks and duration when tools are available.

The helper chooses the largest declared image variant and tries direct MP4 first. For HLS, it checks MP4 renditions matching the manifest variants on Pinterest's CDN. A `.m3u8` manifest or `blob:` URL is not a completed video. A cover image must not be presented as the video. For pins with multiple media items, inspect the chosen item; this version selects one image or video per execution rather than exporting the whole carousel.

Media hosts are restricted to HTTPS on `pinimg.com` and its subdomains. The helper checks content types and file signatures and preserves existing downloads. Inferred HLS rendition paths are used only when the CDN returns a matching MP4 response. The helper requires Python 3.10+ and uses the standard library.

If only streaming segments are available without an MP4 rendition, or the video is embedded from another site, report that limitation and return the pin URL. Do not send the session to third-party download sites. These internal Pinterest structures may change and require extraction updates.

## Deliver

For research, provide selected pins with source links and concrete observations. For downloads, link to the local files and their source pins. Distinguish completed downloads, unavailable content, and failures. Do not claim all videos, original quality, or completion without checking.

This skill does not authorize publishing, following profiles, reacting, messaging, changing boards, or downloading an entire account. Perform those actions only when included in the current user's request.
