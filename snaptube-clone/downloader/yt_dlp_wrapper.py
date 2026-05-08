import yt_dlp
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List


class Downloader:
    """Wrapper around yt-dlp for downloading videos from multiple platforms."""

    SUPPORTED_SITES = [
        "youtube.com", "youtu.be",
        "facebook.com", "fb.com",
        "twitter.com", "x.com",
        "instagram.com",
        "tiktok.com",
        "reddit.com",
        "vimeo.com",
        "dailymotion.com",
        "twitch.tv",
        "linkedin.com",
    ]

    def __init__(self):
        self.download_path: str = str(Path.home() / "Downloads" / "Snaptube-Clone")
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self._cancel_flag: bool = False
        self._current_download: Optional[yt_dlp.YoutubeDL] = None
        self._cached_info: Optional[Dict] = None
        self._cached_info_url: str = ""
        self.cookies_file: Optional[str] = None

        # Ensure download directory exists
        os.makedirs(self.download_path, exist_ok=True)

    def set_cookies(self, cookies_text: str) -> str:
        """Save cookies text to a temp file and return the path."""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="yt_cookies_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(cookies_text)
        self.cookies_file = path
        return path

    def clear_cookies(self):
        """Remove cookies file if set."""
        if self.cookies_file and os.path.exists(self.cookies_file):
            try:
                os.remove(self.cookies_file)
            except Exception:
                pass
        self.cookies_file = None

    def set_download_path(self, path: str):
        """Set custom download directory."""
        self.download_path = path
        os.makedirs(self.download_path, exist_ok=True)

    def _progress_hook(self, d: Dict[str, Any]):
        """Internal progress hook for yt-dlp callbacks."""
        if self._cancel_flag:
            raise Exception("Download cancelled by user.")

        if d["status"] == "downloading":
            percent = d.get("_percent_str", "0%").strip().replace("%", "")
            try:
                percent_float = float(percent)
            except ValueError:
                percent_float = 0.0

            speed = d.get("_speed_str", "N/A").strip()
            eta = d.get("_eta_str", "N/A").strip()

            if self.progress_callback:
                self.progress_callback(percent_float, speed, eta)

            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes", 0) or d.get("total_bytes_estimate", 0)

            if self.status_callback and total > 0:
                self.status_callback(
                    f"Downloading: {self._format_bytes(downloaded)} / {self._format_bytes(total)}"
                )

        elif d["status"] == "finished":
            if self.status_callback:
                self.status_callback("Processing download...")

        elif d["status"] == "error":
            if self.status_callback:
                self.status_callback("Download error occurred!")

    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """Format bytes into human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch video metadata from URL."""
        try:
            ydl_opts: Dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "ignoreerrors": True,
                "nocheckcertificate": True,
                "source_address": "0.0.0.0",
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                "extractor_args": {"youtube": {"skip": ["dash", "hls"], "player_client": ["android", "web"]}},
            }
            if self.cookies_file:
                ydl_opts["cookiefile"] = self.cookies_file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"Error fetching info: {str(e)[:200]}")
            return None

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Get list of available formats for a URL."""
        # Use cached info if available
        if self._cached_info and self._cached_info_url == url:
            info = self._cached_info
        else:
            info = self.get_video_info(url)
            if info:
                self._cached_info = info
                self._cached_info_url = url

        if not info:
            return []

        # Start with the two default options
        result = [
            {"format_id": "bestvideo+bestaudio/best", "label": "🎥 Best Quality (Auto)", "ext": "mp4", "resolution": "Best"},
            {"format_id": "bestaudio/best", "label": "🎵 Best Audio Only (MP3)", "ext": "mp3", "resolution": "Audio Only"},
        ]

        # Collect video+audio combined formats first, then video-only, then audio-only
        combined_formats = []
        video_only_formats = []
        audio_formats = []

        for f in info.get("formats", []):
            format_id = f.get("format_id", "")
            ext = f.get("ext", "")
            resolution = f.get("resolution", "")
            filesize = f.get("filesize", 0) or f.get("filesize_approx", 0)
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            tbr = f.get("tbr", 0)

            has_video = vcodec != "none"
            has_audio = acodec != "none"

            if not has_video and not has_audio:
                continue

            entry = {
                "format_id": format_id,
                "ext": ext,
                "resolution": resolution,
                "filesize": filesize,
                "has_video": has_video,
                "has_audio": has_audio,
                "tbr": tbr,
            }

            if has_video and has_audio:
                entry["label"] = f"{resolution} ({ext})"
                combined_formats.append(entry)
            elif has_video and not has_audio:
                # Only include useful video resolutions
                height = 0
                if "x" in resolution:
                    try: height = int(resolution.split("x")[1])
                    except: pass
                if height >= 360:  # Skip very low res video-only
                    entry["label"] = f"{resolution} ({ext}, video only)"
                    video_only_formats.append(entry)
            elif has_audio and not has_video:
                entry["label"] = f"Audio {tbr:.0f}k ({ext})"
                audio_formats.append(entry)

        # Sort by quality (tbr) descending
        combined_formats.sort(key=lambda x: x.get("tbr", 0), reverse=True)
        video_only_formats.sort(key=lambda x: x.get("tbr", 0), reverse=True)
        audio_formats.sort(key=lambda x: x.get("tbr", 0), reverse=True)

        # Add only the best combined formats (limit to 3)
        seen_res = set()
        for f in combined_formats:
            res = f["resolution"]
            if res not in seen_res:
                seen_res.add(res)
                result.append(f)
            if len(result) >= 8:
                break

        # If we didn't get many combined, add some video-only
        if len(result) < 6:
            for f in video_only_formats[:3]:
                if len(result) < 10:
                    result.append(f)

        return result

    def download(self, url: str, format_id: str = "bestvideo+bestaudio/best",
                 convert_mp3: bool = False) -> bool:
        """Start downloading a video."""
        self._cancel_flag = False

        output_template = os.path.join(self.download_path, "%(title)s.%(ext)s")

        postprocessors = []
        if convert_mp3 or format_id == "bestaudio/best":
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            })

        ydl_opts: Dict[str, Any] = {
            "format": format_id,
            "outtmpl": output_template,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "postprocessors": postprocessors,
            "ignoreerrors": True,
            "nocheckcertificate": True,
            "source_address": "0.0.0.0",
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            "extractor_args": {"youtube": {"skip": ["dash", "hls"], "player_client": ["android", "web"]}},
        }
        if self.cookies_file:
            ydl_opts["cookiefile"] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._current_download = ydl
                ydl.download([url])
                self._current_download = None
                return True
        except Exception as e:
            if self.status_callback:
                error_msg = str(e)
                if "cancel" in error_msg.lower():
                    self.status_callback("⚠️ Download cancelled.")
                else:
                    self.status_callback(f"❌ Download failed: {error_msg[:200]}")
            return False
        finally:
            self._current_download = None

    def cancel_download(self):
        """Cancel the current download."""
        self._cancel_flag = True

    @staticmethod
    def is_supported_url(url: str) -> bool:
        """Check if the URL is from a supported platform."""
        url_lower = url.lower()
        for site in Downloader.SUPPORTED_SITES:
            if site in url_lower:
                return True
        return True

    def download_playlist(self, url: str, format_id: str = "bestvideo+bestaudio/best",
                          max_count: int = 10) -> bool:
        """Download videos from a playlist."""
        self._cancel_flag = False

        output_template = os.path.join(self.download_path, "%(playlist_title)s",
                                       "%(playlist_index)s - %(title)s.%(ext)s")

        ydl_opts = {
            "format": format_id,
            "outtmpl": output_template,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "ignoreerrors": True,
            "max_downloads": max_count,
            "nocheckcertificate": True,
            "source_address": "0.0.0.0",
            "extractor_args": {"youtube": {"skip": ["dash", "hls"], "player_client": ["android", "web"]}},
        }
        if self.cookies_file:
            ydl_opts["cookiefile"] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._current_download = ydl
                ydl.download([url])
                self._current_download = None
                return True
        except Exception as e:
            if self.status_callback:
                error_msg = str(e)
                if "cancel" in error_msg.lower():
                    self.status_callback("⚠️ Playlist download cancelled.")
                else:
                    self.status_callback(f"❌ Playlist download failed: {error_msg[:200]}")
            return False
        finally:
            self._current_download = None