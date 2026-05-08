import customtkinter as ctk
from typing import Optional

from downloader.yt_dlp_wrapper import Downloader
from gui.download_tab import DownloadTab
from gui.settings_tab import SettingsTab
from utils.helpers import load_settings


class MainWindow(ctk.CTk):
    """Main application window with tab-based navigation."""

    def __init__(self):
        super().__init__()

        # Initialize core components
        self.downloader = Downloader()

        # Load settings and apply theme
        self.settings = load_settings()
        theme = self.settings.get("theme", "Dark")
        theme_map = {"Dark": "dark", "Light": "light", "System": "system"}
        ctk.set_appearance_mode(theme_map.get(theme, "dark"))
        ctk.set_default_color_theme("green")

        # Window setup
        self.title("Snaptube Clone - Video Downloader")
        self.geometry("750x680")
        self.minsize(650, 600)

        # Center window
        self._center_window()

        # Set icon (if available)
        try:
            from utils.helpers import get_icon_path
            icon_path = get_icon_path()
            if icon_path:
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # Build the UI
        self._build_ui()

        # Handle close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        """Center window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        """Build the main user interface."""
        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header / Top Bar
        header_frame = ctk.CTkFrame(self, height=50, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        header_label = ctk.CTkLabel(
            header_frame,
            text="🎬 Snaptube Clone - Video Downloader",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header_label.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        # Tab View
        self.tab_view = ctk.CTkTabview(self, corner_radius=8)
        self.tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Download Tab
        self.download_tab_frame = self.tab_view.add("📥 Download")
        self.download_tab = DownloadTab(self.download_tab_frame, self.downloader)
        self.download_tab.pack(fill="both", expand=True)

        # Settings Tab
        self.settings_tab_frame = self.tab_view.add("⚙️ Settings")
        self.settings_tab = SettingsTab(self.settings_tab_frame, self.downloader)
        self.settings_tab.pack(fill="both", expand=True)

        # Status Bar
        status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)

        self.status_bar_label = ctk.CTkLabel(
            status_bar,
            text="✅ Ready | Supported: YouTube, Facebook, TikTok, Instagram, Twitter & more",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.status_bar_label.grid(row=0, column=0, padx=15, pady=5, sticky="w")

    def _on_close(self):
        """Handle window close event."""
        self.downloader.cancel_download()
        self.destroy()

    def run(self):
        """Start the application main loop."""
        self.mainloop()