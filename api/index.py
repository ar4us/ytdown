#!/usr/bin/env python3
"""
ytdown - Video Downloader (Vercel Serverless)
A modern web-based video downloader powered by yt-dlp.
"""
import sys
import os
import uuid
import json
import tempfile
import shutil
from pathlib import Path

# Add project root and api parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

# Create a temp directory for downloads
TEMP_DIR = Path(tempfile.gettempdir()) / "ytdown_downloads"
TEMP_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
CORS(app)

# Store download state
download_state = {}

# ---------- Import yt-dlp helpers ----------
try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def get_downloader():
    """Get a configured yt-dlp instance."""
    return yt_dlp.YoutubeDL if yt_dlp else None


def _format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"


# ---------- Routes ----------
@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def get_info():
    """Fetch video info from URL."""
    if yt_dlp is None:
        return jsonify({"error": "yt-dlp is not installed on the server. Contact the administrator."}), 500

    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"error": "Invalid URL. Must start with http:// or https://"}), 400

    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({"error": "Could not fetch video info. Check the URL and try again."}), 400

        # Build formats list
        formats = [
            {"format_id": "bestvideo+bestaudio/best", "label": "Best Quality (Auto)", "ext": "mp4", "resolution": "Best", "has_video": True},
            {"format_id": "bestaudio/best", "label": "Best Audio Only (MP3)", "ext": "mp3", "resolution": "Audio Only", "has_video": False},
        ]

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
                formats.append(entry)
            elif has_video and not has_audio:
                height = 0
                if "x" in resolution:
                    try:
                        height = int(resolution.split("x")[1])
                    except:
                        pass
                if height >= 360:
                    entry["label"] = f"{resolution} ({ext}, video only)"
                    formats.append(entry)
            elif has_audio and not has_video:
                entry["label"] = f"Audio {tbr:.0f}k ({ext})"
                formats.append(entry)

        return jsonify({
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration_string", "Unknown"),
            "view_count": info.get("view_count", 0),
            "thumbnail": info.get("thumbnail", ""),
            "webpage_url": info.get("webpage_url", url),
            "formats": formats[:15]
        })
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 500


@app.route("/api/download/start", methods=["POST"])
def start_download():
    """Start a download session."""
    if yt_dlp is None:
        return jsonify({"error": "yt-dlp is not installed on the server. Contact the administrator."}), 500

    data = request.get_json()
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "bestvideo+bestaudio/best")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    session_id = str(uuid.uuid4())[:8]
    session_dir = TEMP_DIR / session_id
    session_dir.mkdir(exist_ok=True)

    download_state[session_id] = {
        "url": url,
        "format_id": format_id,
        "progress": 0,
        "speed": "",
        "eta": "",
        "status": "starting",
        "error": None,
        "filename": None,
        "session_dir": str(session_dir),
    }

    try:
        convert_mp3 = format_id == "bestaudio/best"

        output_template = os.path.join(str(session_dir), "%(title)s.%(ext)s")

        postprocessors = []
        if convert_mp3:
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            })

        ydl_opts = {
            "format": format_id,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "postprocessors": postprocessors,
            "ignoreerrors": True,
        }

        last_progress = {"percent": 0, "speed": "", "eta": ""}

        def progress_hook(d):
            if d["status"] == "downloading":
                percent = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    percent_float = float(percent)
                except ValueError:
                    percent_float = 0.0
                last_progress["percent"] = percent_float
                last_progress["speed"] = d.get("_speed_str", "N/A").strip()
                last_progress["eta"] = d.get("_eta_str", "N/A").strip()
                download_state[session_id]["progress"] = percent_float
                download_state[session_id]["speed"] = last_progress["speed"]
                download_state[session_id]["eta"] = last_progress["eta"]
                download_state[session_id]["status"] = "downloading"

        ydl_opts["progress_hooks"] = [progress_hook]

        # Perform download (synchronous, within the request)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the downloaded file
        downloaded_files = list(session_dir.iterdir())
        if downloaded_files:
            # Sort by modification time, newest first
            newest = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            download_state[session_id]["filename"] = newest.name
            download_state[session_id]["progress"] = 100
            download_state[session_id]["status"] = "completed"
        else:
            download_state[session_id]["status"] = "completed"
            download_state[session_id]["progress"] = 100

        return jsonify({
            "session_id": session_id,
            "status": "completed",
            "progress": 100,
            "filename": download_state[session_id].get("filename"),
        })

    except Exception as e:
        error_msg = str(e)[:300]
        download_state[session_id]["status"] = "error"
        download_state[session_id]["error"] = error_msg
        return jsonify({"error": error_msg, "session_id": session_id}), 500


@app.route("/api/download/progress/<session_id>")
def get_progress(session_id):
    """Get download progress."""
    session = download_state.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "progress": session["progress"],
        "speed": session["speed"],
        "eta": session["eta"],
        "status": session["status"],
        "error": session["error"],
        "filename": session.get("filename"),
    })


@app.route("/api/downloads/<session_id>/<path:filename>")
def download_file(session_id, filename):
    """Serve downloaded files."""
    session = download_state.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return send_from_directory(session["session_dir"], filename, as_attachment=True)


@app.route("/api/cleanup/<session_id>", methods=["POST"])
def cleanup(session_id):
    """Clean up a download session."""
    session = download_state.pop(session_id, None)
    if session and os.path.exists(session["session_dir"]):
        shutil.rmtree(session["session_dir"])
    return jsonify({"message": "Cleaned up"})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


# For local development
if __name__ == "__main__":
    print(f"🚀 ytdown Web Server starting...")
    print(f"📁 Temp downloads: {TEMP_DIR}")
    print(f"🌐 Open http://localhost:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=True)