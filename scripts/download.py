#!/usr/bin/env python3
"""Download one Pinterest image or MP4 from read-pin.js metadata. Python 3.10+."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def media_url(value):
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and u.hostname and not u.username and not u.password
                and u.port in (None, 443)
                and (u.hostname == "pinimg.com" or u.hostname.endswith(".pinimg.com")))
    except (TypeError, ValueError, AttributeError):
        return False


class MediaRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not media_url(newurl):
            raise ValueError("The CDN redirected to a disallowed host.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(MediaRedirects())


def open_media(url):
    if not media_url(url):
        raise ValueError("Invalid media URL: use HTTPS on pinimg.com.")
    response = OPENER.open(Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"}), timeout=20)
    if not media_url(response.url):
        response.close()
        raise ValueError("Media response is outside the allowed CDN.")
    return response


def variants(text, base):
    lines = text.splitlines()
    found = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
        for candidate in lines[index + 1:]:
            if not candidate.strip() or candidate.startswith("#"):
                continue
            url = urljoin(base, candidate.strip())
            if media_url(url):
                area = int(resolution[1]) * int(resolution[2]) if resolution else 0
                found.append((area, url))
            break
    return [url for _, url in sorted(found, key=lambda pair: pair[0], reverse=True)]


def mp4_candidates(url):
    source = urlsplit(url)
    if "/videos/iht/hls/" in source.path:
        paths = [source.path]
        try:
            with open_media(url) as response:
                text = response.read(1024 * 1024 + 1)
            if len(text) > 1024 * 1024 or not text.startswith(b"#EXTM3U"):
                raise ValueError("Invalid or oversized HLS manifest.")
            selected = variants(text.decode("utf-8-sig"), url)
            if selected:
                paths = [urlsplit(item).path for item in selected]
        except HTTPError as exc:
            if exc.code == 429:
                raise
        for path in paths[:6]:
            if re.search(r"_\d+w\.m3u8$", path):
                path = path.replace("/iht/hls/", "/iht/expMp4/")[:-5] + ".mp4"
                yield urlunsplit(source._replace(path=path))
    elif "/videos/mc/hls/" in source.path:
        for size in ("1080p", "720p", "480p", "360p"):
            path = source.path.replace("/mc/hls/", f"/mc/{size}/")
            path = re.sub(r"\.m3u8$", ".mp4", path)
            yield urlunsplit(source._replace(path=path))


def signature_matches(data, mime):
    if mime == "video/mp4":
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if mime == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/gif":
        return data[:6] in (b"GIF87a", b"GIF89a")
    if mime == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if mime == "image/avif":
        return data[4:8] == b"ftyp" and (b"avif" in data[8:32] or b"avis" in data[8:32])
    return False


EXTENSIONS = {"video/mp4": ".mp4", "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp", "image/avif": ".avif"}


def save(url, pin_id, kind, directory, limit):
    with open_media(url) as response:
        mime = response.headers.get_content_type()
        first = response.read(64)
        if kind == "video" and mime == "application/octet-stream" and signature_matches(first, "video/mp4"):
            mime = "video/mp4"
        if not mime.startswith("image/" if kind == "image" else "video/") or not signature_matches(first, mime):
            raise ValueError("The response is not a supported image or MP4.")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > limit:
            raise ValueError("The file exceeds the configured size limit.")
        directory.mkdir(parents=True, exist_ok=True)
        index = 1
        while True:
            suffix = "" if index == 1 else f"-{index}"
            path = directory / f"pinterest-{pin_id}{suffix}{EXTENSIONS[mime]}"
            try:
                output = path.open("xb")
                break
            except FileExistsError:
                index += 1
        count = 0
        digest = hashlib.sha256()
        try:
            with output:
                chunk = first
                while chunk:
                    count += len(chunk)
                    if count > limit:
                        raise ValueError("The file exceeds the configured size limit.")
                    output.write(chunk)
                    digest.update(chunk)
                    chunk = response.read(128 * 1024)
            if declared and count != int(declared):
                raise ValueError("Incomplete download: byte count does not match the CDN response.")
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return {"path": str(path.resolve()), "bytes": count, "mime": mime, "sha256": digest.hexdigest()}


def download(metadata, kind, directory, limit):
    if not isinstance(metadata, dict):
        raise ValueError("The JSON must contain the object returned by read-pin.js.")
    pin_id = metadata.get("pinId")
    if not isinstance(pin_id, str) or not re.fullmatch(r"\d{3,30}", pin_id):
        raise ValueError("Invalid pinId in metadata JSON.")
    pin_url = urlsplit(metadata.get("url", ""))
    if (pin_url.scheme != "https" or not pin_url.hostname or pin_url.username or pin_url.password
            or not (pin_url.hostname == "pinterest.com" or pin_url.hostname.endswith(".pinterest.com"))
            or pin_url.path.rstrip("/") != f"/pin/{pin_id}"):
        raise ValueError("The source URL does not match pinId.")
    formats = metadata.get("images" if kind == "image" else "formats", [])
    formats = sorted((f for f in formats if isinstance(f, dict) and media_url(f.get("url"))),
                     key=lambda f: (f.get("width") or 0) * (f.get("height") or 0), reverse=True)
    direct = [f["url"] for f in formats if kind == "image" or re.search(r"\.mp4(?:\?|$)", f["url"], re.I)]
    seen = set()
    last_error = None
    def try_urls(urls):
        nonlocal last_error
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            try:
                return save(url, pin_id, kind, directory, limit)
            except HTTPError as exc:
                if exc.code == 429:
                    raise ValueError("Pinterest rate-limited the downloads. Wait before trying again.") from exc
                last_error = exc
            except (URLError, TimeoutError, ValueError, OSError) as exc:
                last_error = exc
        return None
    result = try_urls(direct)
    if result is None and kind == "video":
        for item in formats:
            if not re.search(r"\.m3u8(?:\?|$)", item["url"], re.I):
                continue
            try:
                result = try_urls(mp4_candidates(item["url"]))
            except HTTPError as exc:
                if exc.code == 429:
                    raise ValueError("Pinterest rate-limited the downloads. Wait before trying again.") from exc
                last_error = exc
            except (URLError, TimeoutError, ValueError, OSError) as exc:
                last_error = exc
            if result:
                break
    if result is None:
        detail = f" Last response: {last_error}" if last_error else ""
        raise ValueError("No compatible media file was found for this pin." + detail)
    return {**result, "pinUrl": metadata["url"], "pinId": pin_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--kind", required=True, choices=("image", "video"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-mib", type=int, default=512)
    args = parser.parse_args()
    try:
        if args.max_mib <= 0:
            raise ValueError("--max-mib must be positive.")
        metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
        result = download(metadata, args.kind, args.output_dir, args.max_mib * 1024 * 1024)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, TypeError, KeyError, OSError, URLError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
