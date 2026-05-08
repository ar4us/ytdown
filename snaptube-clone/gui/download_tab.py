import customtkinter as ctk
import threading
import time
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any

from downloader.yt_dlp_wrapper import Downloader
from utils.helpers import is_valid_url, extract_domain, open_download_folder, load_settings


class DownloadTab(ctk.CTkFrame):
    """Main download tab where users paste URLs and manage downloads."""

    def __init__(self, parent, downloader: Downloader):
        super().__init__(parent)
        self.downloader = downloader
        self.is_downloading = False
        self.current_info: Optional[Dict[str, Any]] = None
        self.selected_format: str = "bestvideo+bestaudio/best"
        self.convert_to_mp3: bool = False
        self._last_progress_update = time.time()
        self._progress_throttle = 0.1  # Max 10 updates per second

        # Connect callbacks (these will be called from the download thread!)
        self.downloader.progress_callback = self._on_progress_threadsafe
        self.downloader.status_callback = self._on_status_threadsafe

        self._build_ui()
        self._load_last_path()

    def _build_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title
        title = ctk.CTkLabel(
            self, text="📥 Download Video",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        # URL Input Section
        url_frame = ctk.CTkFrame(self)
        url_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        url_frame.grid_columnconfigure(1, weight=1)

        url_label = ctk.CTkLabel(url_frame, text="🔗 URL:", font=ctk.CTkFont(size=14))
        url_label.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")

        self.url_entry = ctk.CTkEntry(
            url_frame, placeholder_text="Paste video URL here... (YouTube, Facebook, TikTok, etc.)",
            font=ctk.CTkFont(size=13),
            height=40
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=15, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self._fetch_info())

        self.fetch_btn = ctk.CTkButton(
            url_frame, text="🔍 Get Info",
            command=self._fetch_info,
            height=40,
            width=100,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.fetch_btn.grid(row=0, column=2, padx=(5, 15), pady=15)

        # Video Info Section
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        self.info_frame.grid_rowconfigure(1, weight=1)

        # Info header
        self.info_header = ctk.CTkLabel(
            self.info_frame, text="ℹ️ Video Info",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.info_header.grid(row=0, column=0, pady=(10, 5), padx=15, sticky="w")

        # Info display area
        self.info_text = ctk.CTkTextbox(
            self.info_frame, height=120,
            font=ctk.CTkFont(size=12),
            wrap="word",
            state="disabled"
        )
        self.info_text.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="nsew")

        # Format selection
        format_frame = ctk.CTkFrame(self.info_frame)
        format_frame.grid(row=2, column=0, padx=15, pady=(5, 5), sticky="ew")
        format_frame.grid_columnconfigure(1, weight=1)

        format_label = ctk.CTkLabel(
            format_frame, text="📀 Quality:",
            font=ctk.CTkFont(size=13)
        )
        format_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.format_combo = ctk.CTkComboBox(
            format_frame,
            values=["Fetching formats..."],
            state="readonly",
            width=350,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.format_combo.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.format_combo.set("Fetch formats first")

        self.mp3_var = ctk.BooleanVar(value=False)
        self.mp3_check = ctk.CTkCheckBox(
            format_frame, text="🎵 Convert to MP3",
            variable=self.mp3_var,
            command=self._toggle_mp3,
            font=ctk.CTkFont(size=12)
        )
        self.mp3_check.grid(row=0, column=2, padx=(10, 10), pady=10)

        # Progress Section
        progress_frame = ctk.CTkFrame(self.info_frame)
        progress_frame.grid(row=3, column=0, padx=15, pady=(5, 10), sticky="ew")
        progress_frame.grid_columnconfigure(1, weight=1)

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=12)
        self.progress_bar.grid(row=0, column=0, columnspan=3, padx=15, pady=(10, 0), sticky="ew")
        self.progress_bar.set(0)

        self.percent_label = ctk.CTkLabel(
            progress_frame, text="0%",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.percent_label.grid(row=1, column=0, padx=(15, 5), pady=(5, 10), sticky="w")

        self.speed_label = ctk.CTkLabel(
            progress_frame, text="",
            font=ctk.CTkFont(size=12)
        )
        self.speed_label.grid(row=1, column=1, padx=5, pady=(5, 10), sticky="w")

        self.status_label = ctk.CTkLabel(
            progress_frame, text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=1, column=2, padx=(5, 15), pady=(5, 10), sticky="e")

        # Action Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        self.download_btn = ctk.CTkButton(
            button_frame, text="⬇️ Download",
            command=self._start_download,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60",
            state="disabled"
        )
        self.download_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.cancel_btn = ctk.CTkButton(
            button_frame, text="❌ Cancel",
            command=self._cancel_download,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled"
        )
        self.cancel_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.open_btn = ctk.CTkButton(
            button_frame, text="📂 Open Folder",
            command=lambda: open_download_folder(self.downloader.download_path),
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.open_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

    def _load_last_path(self):
        settings = load_settings()
        if settings.get("download_path"):
            self.downloader.set_download_path(settings["download_path"])

    def _toggle_mp3(self):
        self.convert_to_mp3 = self.mp3_var.get()
        if self.convert_to_mp3:
            self.format_combo.set("🎵 Audio Only (MP3)")
            self.selected_format = "bestaudio/best"
        elif self.current_info and self.format_combo.get() == "🎵 Audio Only (MP3)":
            self.format_combo.set("🎥 Best Quality (Auto)")
            self.selected_format = "bestvideo+bestaudio/best"

    def _on_progress_threadsafe(self, percent: float, speed: str, eta: str):
        """Thread-safe progress handler - uses after() to update UI on main thread."""
        now = time.time()
        if now - self._last_progress_update < self._progress_throttle:
            return
        self._last_progress_update = now
        # Schedule the UI update on the main thread
        self.after(0, self._update_progress_ui, percent, speed, eta)

    def _update_progress_ui(self, percent: float, speed: str, eta: str):
        """Update progress widgets (must be called from main thread)."""
        try:
            self.progress_bar.set(percent / 100.0)
            self.percent_label.configure(text=f"{percent:.1f}%")
            text = f"⚡ {speed}" if speed and speed != "N/A" else ""
            if eta and eta != "N/A":
                text += f" | ⏱ {eta}"
            self.speed_label.configure(text=text)
        except Exception:
            pass  # Widget might be destroyed

    def _on_status_threadsafe(self, message: str):
        """Thread-safe status handler - uses after() to update UI on main thread."""
        self.after(0, self._update_status_ui, message)

    def _update_status_ui(self, message: str):
        """Update status label (must be called from main thread)."""
        try:
            self.status_label.configure(text=message)
        except Exception:
            pass

    def _fetch_info(self):
        """Fetch video info and formats in a background thread."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please paste a URL first!")
            return
        if not is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid URL!\nExample: https://www.youtube.com/watch?v=...")
            return

        # Disable fetch button
        self.fetch_btn.configure(state="disabled", text="⏳ Loading...")
        self.status_label.configure(text="Fetching video info...")
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "Fetching information... please wait...")
        self.info_text.configure(state="disabled")

        # Run in thread
        thread = threading.Thread(target=self._do_fetch_info, args=(url,), daemon=True)
        thread.start()

    def _do_fetch_info(self, url: str):
        """Background task to fetch video info."""
        domain = extract_domain(url)
        try:
            # Fetch info once - get_available_formats caches it
            info = self.downloader.get_video_info(url)
            if info:
                # Now get formats - uses cached info
                formats = self.downloader.get_available_formats(url)
            else:
                formats = []
        except Exception as e:
            info = None
            formats = []
            error_msg = str(e)[:200]

        # Update UI in main thread
        self.after(0, self._display_info, url, domain, info, formats)

    def _display_info(self, url: str, domain: str, info: Optional[Dict], formats: list):
        """Display fetched video info in UI."""
        self.fetch_btn.configure(state="normal", text="🔍 Get Info")

        if not info:
            self.status_label.configure(text="❌ Could not fetch video info. Check URL and try again.")
            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", "Error: Could not retrieve video information.\n"
                                        "Possible reasons:\n"
                                        "• The URL may be invalid\n"
                                        "• The video may be private/removed\n"
                                        "• yt-dlp may need an update\n"
                                        "• The site may have restrictions")
            self.info_text.configure(state="disabled")
            return

        self.current_info = info
        title = info.get("title", "Unknown")
        duration = info.get("duration_string", "Unknown")
        uploader = info.get("uploader", "Unknown")
        view_count = info.get("view_count", 0)
        webpage_url = info.get("webpage_url", url)

        # Format view count
        if view_count:
            view_count = f"{view_count:,}"

        # Display info
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        info_text = (
            f"📹 Title: {title}\n"
            f"👤 Uploader: {uploader}\n"
            f"⏱ Duration: {duration}\n"
            f"👁 Views: {view_count}\n"
            f"🌐 Source: {domain}\n"
            f"🔗 URL: {webpage_url}"
        )
        self.info_text.insert("1.0", info_text)
        self.info_text.configure(state="disabled")

        # Update formats dropdown
        if formats:
            format_labels = [f["label"] for f in formats]
            self.format_combo.configure(values=format_labels)
            self.format_combo.set(format_labels[0])
            self.selected_format = formats[0]["format_id"]
        else:
            self.format_combo.configure(values=["Best available"])
            self.format_combo.set("Best available")
            self.selected_format = "best"

        # Enable download button
        self.download_btn.configure(state="normal")
        self.status_label.configure(text="✅ Ready to download")
        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")
        self.speed_label.configure(text="")

    def _start_download(self):
        """Start the download in a background thread."""
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            return

        # Get selected format from combo box - just use the already known selected_format
        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ Downloading...")
        self.cancel_btn.configure(state="normal")
        self.fetch_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")

        self.progress_bar.set(0)
        self.status_label.configure(text="Starting download...")

        thread = threading.Thread(
            target=self._do_download,
            args=(url, self.selected_format, self.convert_to_mp3),
            daemon=True
        )
        thread.start()

    def _do_download(self, url: str, format_id: str, convert_mp3: bool):
        """Background download task."""
        try:
            success = self.downloader.download(url, format_id, convert_mp3)
        except Exception as e:
            success = False
        self.after(0, self._download_finished, success)

    def _download_finished(self, success: bool):
        """Handle download completion."""
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ Download")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.url_entry.configure(state="normal")

        if success:
            self.status_label.configure(text="✅ Download completed successfully!")
            self.progress_bar.set(1.0)
            self.percent_label.configure(text="100%")
            messagebox.showinfo(
                "Download Complete",
                f"Video downloaded successfully!\n\n📁 Location: {self.downloader.download_path}"
            )
        else:
            self.status_label.configure(text="❌ Download failed or cancelled")
            self.progress_bar.set(0)

    def _cancel_download(self):
        """Cancel the current download."""
        self.downloader.cancel_download()
        self.status_label.configure(text="⏹ Cancelling download...")
        self.cancel_btn.configure(state="disabled")