import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

from downloader.yt_dlp_wrapper import Downloader
from utils.helpers import load_settings, save_settings, open_download_folder


class SettingsTab(ctk.CTkFrame):
    """Settings tab for configuring download paths and preferences."""

    def __init__(self, parent, downloader: Downloader):
        super().__init__(parent)
        self.downloader = downloader
        self.settings = load_settings()

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            self, text="⚙️ Settings",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 20), padx=20, sticky="w")

        # Download Path Section
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        path_label = ctk.CTkLabel(
            path_frame, text="📁 Download Location:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        path_label.grid(row=0, column=0, padx=(15, 10), pady=(15, 5), sticky="w")

        self.path_var = ctk.StringVar(value=self.settings.get("download_path", ""))
        self.path_entry = ctk.CTkEntry(
            path_frame, textvariable=self.path_var,
            font=ctk.CTkFont(size=13),
            height=35
        )
        self.path_entry.grid(row=1, column=0, columnspan=2, padx=(15, 5), pady=(0, 15), sticky="ew")

        self.browse_btn = ctk.CTkButton(
            path_frame, text="📂 Browse",
            command=self._browse_path,
            height=35,
            width=100,
            font=ctk.CTkFont(size=12)
        )
        self.browse_btn.grid(row=1, column=2, padx=(5, 15), pady=(0, 15))

        # Theme Section
        theme_frame = ctk.CTkFrame(self)
        theme_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        theme_frame.grid_columnconfigure(1, weight=1)

        theme_label = ctk.CTkLabel(
            theme_frame, text="🎨 Theme:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        theme_label.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="w")

        self.theme_var = ctk.StringVar(value=self.settings.get("theme", "Dark"))
        self.theme_combo = ctk.CTkComboBox(
            theme_frame,
            values=["Dark", "Light", "System"],
            variable=self.theme_var,
            state="readonly",
            width=200,
            height=35,
            font=ctk.CTkFont(size=13),
            command=self._change_theme
        )
        self.theme_combo.grid(row=0, column=1, padx=5, pady=15, sticky="w")

        # Playlist Section
        playlist_frame = ctk.CTkFrame(self)
        playlist_frame.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        playlist_frame.grid_columnconfigure(1, weight=1)

        playlist_label = ctk.CTkLabel(
            playlist_frame, text="🔢 Max Playlist Items:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        playlist_label.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="w")

        self.playlist_var = ctk.StringVar(
            value=str(self.settings.get("max_playlist_items", 10))
        )
        self.playlist_spinbox = ctk.CTkEntry(
            playlist_frame, textvariable=self.playlist_var,
            width=80, height=35,
            font=ctk.CTkFont(size=13)
        )
        self.playlist_spinbox.grid(row=0, column=1, padx=5, pady=15, sticky="w")

        playlist_hint = ctk.CTkLabel(
            playlist_frame, text="(1-50)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        playlist_hint.grid(row=0, column=2, padx=(5, 15), pady=15, sticky="w")

        # Auto-open folder
        auto_frame = ctk.CTkFrame(self)
        auto_frame.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.auto_open_var = ctk.BooleanVar(
            value=self.settings.get("auto_open_folder", False)
        )
        self.auto_open_check = ctk.CTkCheckBox(
            auto_frame, text="📂 Auto-open folder after download",
            variable=self.auto_open_var,
            font=ctk.CTkFont(size=13)
        )
        self.auto_open_check.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(
            button_frame, text="💾 Save Settings",
            command=self._save_settings_handler,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        self.save_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.reset_btn = ctk.CTkButton(
            button_frame, text="🔄 Reset Defaults",
            command=self._reset_settings,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#e67e22",
            hover_color="#d35400"
        )
        self.reset_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Info / about section
        about_frame = ctk.CTkFrame(self)
        about_frame.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")

        about_label = ctk.CTkLabel(
            about_frame,
            text="📱 Snaptube-Clone v1.0.0\n"
                 "Powered by yt-dlp 🎬\n"
                 "Supports: YouTube, Facebook, TikTok, Instagram, Twitter, and more!",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        about_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

    def _browse_path(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(
            title="Select Download Folder",
            initialdir=self.path_var.get() or str(Path.home() / "Downloads")
        )
        if folder:
            self.path_var.set(folder)

    def _change_theme(self, choice: str):
        """Change the application theme."""
        theme_map = {
            "Dark": "dark",
            "Light": "light",
            "System": "system"
        }
        ctk.set_appearance_mode(theme_map.get(choice, "dark"))

    def _save_settings_handler(self):
        """Save all settings."""
        # Validate playlist count
        try:
            max_items = int(self.playlist_var.get())
            if max_items < 1 or max_items > 50:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Playlist items must be between 1 and 50!")
            return

        new_settings = {
            "download_path": self.path_var.get(),
            "theme": self.theme_var.get(),
            "max_playlist_items": max_items,
            "auto_open_folder": self.auto_open_var.get(),
        }

        save_settings(new_settings)
        self.settings.update(new_settings)

        # Apply to downloader
        self.downloader.set_download_path(new_settings["download_path"])

        messagebox.showinfo("Success", "Settings saved successfully!")

    def _reset_settings(self):
        """Reset settings to defaults."""
        defaults = {
            "download_path": str(Path.home() / "Downloads" / "Snaptube-Clone"),
            "theme": "Dark",
            "max_playlist_items": 10,
            "auto_open_folder": False,
        }

        self.path_var.set(defaults["download_path"])
        self.theme_var.set(defaults["theme"])
        self.playlist_var.set(str(defaults["max_playlist_items"]))
        self.auto_open_var.set(defaults["auto_open_folder"])

        ctk.set_appearance_mode("dark")

        messagebox.showinfo("Reset", "Settings reset to defaults. Click 'Save Settings' to apply.")