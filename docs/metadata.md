# Pin metadata

Run `scripts/read-pin.js` through a browser JavaScript evaluation tool while the exact pin is open. Save the returned object as UTF-8 JSON for `scripts/download.py`.

The browser script returns:

| Field | Type | Meaning |
| --- | --- | --- |
| `pinId` | string | Numeric Pinterest pin ID, 3–30 digits. |
| `url` | string | Canonical HTTPS pin URL on Pinterest; must match `pinId`. |
| `title` | string | Available pin title; may be empty. |
| `description` | string | Available pin description; may be empty. |
| `pinnedBy` | string or null | Pinning profile's name, not proof of original authorship. |
| `images` | array | Declared image variants, sorted by pixel area. |
| `formats` | array | Direct video or HLS formats, sorted by pixel area. |

Every image variant has `url`, `width`, and `height`. Video formats additionally have `durationMs`, which can be null. URLs must use HTTPS on `pinimg.com` or its subdomains; the downloader also validates redirects.

For an image download, the helper reads `pinId`, `url`, and `images`. For video it reads `pinId`, `url`, and `formats`. Titles and profile names are not used to build filenames. Keep tool response envelopes and Markdown fences out of the JSON.

A pin may legitimately have image variants and an empty video format list. A video pin's image variants represent its cover image. Selecting `--kind image` downloads an image, not the video.

## Result

Success is one JSON object on standard output:

- `path`: absolute local path.
- `bytes`: number of bytes written.
- `mime`: validated media content type.
- `sha256`: SHA-256 of the saved bytes.
- `pinUrl` and `pinId`: original pin reference.

Errors are JSON on standard error with a nonzero exit status. Existing files are preserved; suffixes are added for repeated downloads. The file size limit defaults to 512 MiB and can be changed with `--max-mib`.
