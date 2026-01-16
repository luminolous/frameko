class FramekoError(Exception):
    """Base exception for frameko."""


class DependencyMissingError(FramekoError):
    """Raised when an optional dependency is required but not installed."""


class ExternalToolMissingError(FramekoError):
    """Raised when ffmpeg/ffprobe (or other external tools) are missing."""


class ConfigError(FramekoError):
    """Raised when config/preset is invalid."""
