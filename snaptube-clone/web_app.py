#!/usr/bin/env python3
"""
Snaptube Clone - Web Version
A modern web-based video downloader powered by yt-dlp.
"""
import sys
import os
import uuid
import threading
from pathlib import Path

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from downloader.yt_dlp_wrapper import Downloader

app = Flask(__name__)
CORS(app)

## Store download sessions
downloads = {}
downloader = Downloader()

# Main download directory
BASE_DOWNLOAD_DIR = Path.home() / "SnaptubeDownloads"
BASE_DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def get_info():
    """Fetch video info from URL."""
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"error": "Invalid URL. Must start with http:// or https://"}), 400

    try:
        info = downloader.get_video_info(url)
        if not info:
            return jsonify({"error": "Could not fetch video info. Check the URL and try again."}), 400

        formats = downloader.get_available_formats(url)

        return jsonify({
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration_string", "Unknown"),
            "view_count": info.get("view_count", 0),
            "thumbnail": info.get("thumbnail", ""),
            "webpage_url": info.get("webpage_url", url),
            "formats": formats
        })
    except Exception as e:
        error_msg = str(e)
        if "confirm you're not a bot" in error_msg.lower() or "sign in to confirm" in error_msg.lower():
            return jsonify({"error": "YouTube bot detection triggered. Please provide cookies in Settings to bypass this."}), 403
        return jsonify({"error": error_msg[:300]}), 500


@app.route("/api/download/start", methods=["POST"])
def start_download():
    """Start a download session."""
    data = request.get_json()
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "bestvideo+bestaudio/best")
    convert_mp3 = data.get("convert_mp3", False)

    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Create a download session
    session_id = str(uuid.uuid4())[:8]
    session_dir = BASE_DOWNLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)

    downloads[session_id] = {
        "url": url,
        "format_id": format_id,
        "convert_mp3": convert_mp3,
        "progress": 0,
        "speed": "",
        "eta": "",
        "status": "starting",
        "error": None,
        "filename": None,
        "session_dir": str(session_dir)
    }

    # Start download in background thread
    thread = threading.Thread(
        target=_do_download,
        args=(session_id, url, format_id, convert_mp3),
        daemon=True
    )
    thread.start()

    return jsonify({"session_id": session_id})


def _do_download(session_id, url, format_id, convert_mp3):
    """Background download task."""
    session_dir = Path(downloads[session_id]["session_dir"])

    def progress_cb(percent, speed, eta):
        if session_id in downloads:
            downloads[session_id]["progress"] = percent
            downloads[session_id]["speed"] = speed
            downloads[session_id]["eta"] = eta
            downloads[session_id]["status"] = "downloading"

    def status_cb(message):
        if session_id in downloads:
            if "Error" in message or "failed" in message.lower():
                downloads[session_id]["status"] = "error"
                downloads[session_id]["error"] = message
            elif "completed" in message.lower():
                downloads[session_id]["status"] = "completed"
                downloads[session_id]["progress"] = 100
            elif "cancel" in message.lower():
                downloads[session_id]["status"] = "cancelled"
            elif "processing" in message.lower():
                downloads[session_id]["status"] = "processing"
            
            # Special check for bot detection
            if "confirm you're not a bot" in message.lower() or "sign in to confirm" in message.lower():
                downloads[session_id]["status"] = "error"
                downloads[session_id]["error"] = "YouTube bot detection. Please add cookies in Settings."

    # Create a fresh downloader for this session to avoid callback conflicts
    session_downloader = Downloader()
    session_downloader.set_download_path(str(session_dir))
    session_downloader.progress_callback = progress_cb
    session_downloader.status_callback = status_cb
    
    # Pass global cookies to this session
    if downloader.cookies_file:
        try:
            with open(downloader.cookies_file, "r", encoding="utf-8") as f:
                session_downloader.set_cookies(f.read())
        except Exception:
            pass

    try:
        success = session_downloader.download(url, format_id, convert_mp3)
        if success and session_id in downloads:
            if downloads[session_id]["status"] not in ["error", "cancelled"]:
                downloads[session_id]["status"] = "completed"
                downloads[session_id]["progress"] = 100
                # Find the latest file in session directory
                try:
                    files = sorted(session_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
                    # Filter out temp files or cookies files if any
                    files = [f for f in files if not f.name.startswith("yt_cookies_")]
                    if files:
                        downloads[session_id]["filename"] = files[0].name
                except Exception:
                    pass
    except Exception as e:
        if session_id in downloads:
            downloads[session_id]["status"] = "error"
            downloads[session_id]["error"] = str(e)[:300]
    finally:
        # Cleanup session cookies if any
        session_downloader.clear_cookies()


# ---------- Cookie management ----------
@app.route("/api/cookies", methods=["GET"])
def get_cookies_status():
    """Check if cookies are configured."""
    return jsonify({"has_cookies": downloader.cookies_file is not None})


@app.route("/api/cookies", methods=["POST"])
def set_cookies():
    """Set YouTube cookies from pasted text."""
    data = request.get_json()
    cookies_text = data.get("cookies", "").strip()

    if not cookies_text:
        return jsonify({"error": "Cookie text is required"}), 400

    try:
        path = downloader.set_cookies(cookies_text)
        return jsonify({"message": "Cookies saved successfully", "path": path})
    except Exception as e:
        return jsonify({"error": f"Failed to save cookies: {str(e)[:200]}"}), 500


@app.route("/api/cookies", methods=["DELETE"])
def clear_cookies():
    """Clear stored cookies."""
    downloader.clear_cookies()
    return jsonify({"message": "Cookies cleared"})


@app.route("/api/download/progress/<session_id>")
def get_progress(session_id):
    """Get download progress."""
    session = downloads.get(session_id)
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


@app.route("/api/download/cancel/<session_id>", methods=["POST"])
def cancel_download(session_id):
    """Cancel a download session."""
    # Note: Global downloader cancel might affect other sessions if not careful,
    # but here we are using session_downloader in threads which aren't easily accessible.
    # For now, we set the status to cancelled.
    if session_id in downloads:
        downloads[session_id]["status"] = "cancelled"
    return jsonify({"message": "Download cancelled"})


@app.route("/api/downloads/<session_id>/<path:filename>")
def download_file(session_id, filename):
    """Serve downloaded files from session directory."""
    session = downloads.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return send_from_directory(session["session_dir"], filename, as_attachment=True)


@app.route("/api/cleanup/<session_id>", methods=["POST"])
def cleanup(session_id):
    """Clean up a download session and its files."""
    session = downloads.pop(session_id, None)
    if session and "session_dir" in session:
        try:
            shutil.rmtree(session["session_dir"])
        except Exception:
            pass
    return jsonify({"message": "Cleaned up"})


@app.route("/api/files")
def list_files():
    """List all downloaded files (across all active sessions)."""
    files = []
    for session in downloads.values():
        if "session_dir" in session and os.path.exists(session["session_dir"]):
            s_dir = Path(session["session_dir"])
            for f in s_dir.iterdir():
                if f.is_file() and not f.name.startswith("yt_cookies_"):
                    files.append({
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime,
                        "session_id": os.path.basename(session["session_dir"])
                    })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify(files)


if __name__ == "__main__":
    import shutil
    print(f"🚀 Snaptube Clone Web Server starting...")
    print(f"📁 Downloads saved to: {BASE_DOWNLOAD_DIR}")
    print(f"🌐 Open http://localhost:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)