import hashlib
import importlib.util
import io
from email.message import Message
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "download.py"
spec = importlib.util.spec_from_file_location("pinscout_download", SCRIPT)
downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloader)

PIN_ID = "123456789"
PIN_URL = f"https://www.pinterest.com/pin/{PIN_ID}/"
IMAGE_URL = "https://i.pinimg.com/originals/test/image.jpg"
JPEG = b"\xff\xd8\xff" + b"synthetic-test-bytes" * 10
MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isom" + b"synthetic-test-bytes" * 10


class Response(io.BytesIO):
    def __init__(self, body, url, mime, length=None, include_length=True):
        super().__init__(body)
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = mime
        if include_length:
            self.headers["Content-Length"] = str(len(body) if length is None else length)


class DownloadTests(unittest.TestCase):
    def test_existing_file_is_preserved_and_new_file_has_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / f"pinterest-{PIN_ID}.jpg"
            original.write_bytes(b"existing-file")
            with patch.object(downloader, "open_media", return_value=Response(JPEG, IMAGE_URL, "image/jpeg")):
                result = downloader.save(IMAGE_URL, PIN_ID, "image", root, 1024)
            self.assertEqual(original.read_bytes(), b"existing-file")
            self.assertEqual(Path(result["path"]).name, f"pinterest-{PIN_ID}-2.jpg")
            self.assertEqual(Path(result["path"]).read_bytes(), JPEG)
            self.assertEqual(result["sha256"], hashlib.sha256(JPEG).hexdigest())

    def test_html_with_image_header_does_not_create_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(downloader, "open_media", return_value=Response(b"<html>error</html>", IMAGE_URL, "image/jpeg")):
                with self.assertRaises(ValueError):
                    downloader.save(IMAGE_URL, PIN_ID, "image", root, 1024)
            self.assertEqual(list(root.iterdir()), [])

    def test_truncated_transfer_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(downloader, "open_media", return_value=Response(JPEG, IMAGE_URL, "image/jpeg", length=len(JPEG) + 10)):
                with self.assertRaises(ValueError):
                    downloader.save(IMAGE_URL, PIN_ID, "image", root, 1024)
            self.assertEqual(list(root.iterdir()), [])

    def test_streaming_limit_without_content_length_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(downloader, "open_media", return_value=Response(JPEG, IMAGE_URL, "image/jpeg", include_length=False)):
                with self.assertRaises(ValueError):
                    downloader.save(IMAGE_URL, PIN_ID, "image", root, 80)
            self.assertEqual(list(root.iterdir()), [])

    def test_mismatched_pin_is_rejected_before_a_network_request(self):
        metadata = {"pinId": PIN_ID, "url": "https://www.pinterest.com/pin/999999/", "images": [{"url": IMAGE_URL}]}
        with patch.object(downloader, "open_media") as request:
            with self.assertRaises(ValueError):
                downloader.download(metadata, "image", Path("unused"), 1024)
            request.assert_not_called()

    def test_external_redirect_is_rejected(self):
        with self.assertRaises(ValueError):
            downloader.MediaRedirects().redirect_request(None, None, 302, "Found", {}, "https://pinimg.com.example.org/file.mp4")

    def test_untrusted_media_host_is_not_requested(self):
        metadata = {"pinId": PIN_ID, "url": PIN_URL, "images": [{"url": "https://evilpinimg.com/image.jpg"}]}
        with patch.object(downloader, "open_media") as request:
            with self.assertRaises(ValueError):
                downloader.download(metadata, "image", Path("unused"), 1024)
            request.assert_not_called()

    def test_hls_metadata_downloads_highest_available_mp4_rendition(self):
        hls = "https://v1.pinimg.com/videos/iht/hls/test/video.m3u8"
        mp4 = "https://v1.pinimg.com/videos/iht/expMp4/test/video_720w.mp4"
        playlist = ("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000,RESOLUTION=360x640\nvideo_360w.m3u8\n"
                    "#EXT-X-STREAM-INF:BANDWIDTH=2000,RESOLUTION=720x1280\nvideo_720w.m3u8\n").encode()
        calls = []

        def response(url):
            calls.append(url)
            if url == hls:
                return Response(playlist, url, "application/vnd.apple.mpegurl")
            self.assertEqual(url, mp4)
            return Response(MP4, url, "video/mp4")

        metadata = {"pinId": PIN_ID, "url": PIN_URL, "formats": [{"url": hls}]}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(downloader, "open_media", side_effect=response):
                result = downloader.download(metadata, "video", Path(directory), 1024)
            self.assertEqual(Path(result["path"]).read_bytes(), MP4)
            self.assertEqual(result["mime"], "video/mp4")
            self.assertEqual(result["pinUrl"], PIN_URL)
            self.assertEqual(calls, [hls, mp4])


if __name__ == "__main__":
    unittest.main()
