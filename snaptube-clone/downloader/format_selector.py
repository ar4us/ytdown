from typing import Dict, Any, List, Optional


class FormatSelector:
    """Helper class to filter and organize video formats."""

    @staticmethod
    def filter_best_video(formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return only video formats with the best resolution."""
        video_formats = [f for f in formats if f.get("has_video")]
        return sorted(video_formats, key=lambda x: x.get("tbr", 0), reverse=True)[:5]

    @staticmethod
    def filter_audio_only(formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return only audio formats."""
        audio = [f for f in formats if not f.get("has_video") and f.get("has_audio")]
        return sorted(audio, key=lambda x: x.get("tbr", 0), reverse=True)[:5]

    @staticmethod
    def get_quality_rank(label: str) -> int:
        """Get a numeric quality rank for sorting."""
        if "4K" in label or "2160" in label:
            return 5
        if "1440" in label or "2K" in label:
            return 4
        if "1080" in label:
            return 3
        if "720" in label:
            return 2
        if "480" in label:
            return 1
        return 0

    @staticmethod
    def format_size(filesize: int) -> str:
        """Format file size for display."""
        if not filesize:
            return "Unknown size"
        for unit in ["B", "KB", "MB", "GB"]:
            if filesize < 1024:
                return f"{filesize:.1f} {unit}"
            filesize /= 1024
        return f"{filesize:.1f} TB"

    @staticmethod
    def is_playlist(info: Dict[str, Any]) -> bool:
        """Check if the info represents a playlist."""
        return info.get("_type") == "playlist" or "entries" in info