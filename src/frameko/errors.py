from __future__ import annotations


class FramekoError(RuntimeError):
    """Base error for frameko."""


class DependencyMissingError(FramekoError):
    """Raised when an optional dependency is required but not installed."""


class ExternalToolMissingError(FramekoError):
    """Raised when ffmpeg/ffprobe are not available."""


class VideoProbeError(FramekoError):
    """Raised when ffprobe cannot parse a video."""


class ExtractionError(FramekoError):
    """Raised when ffmpeg cannot extract a frame."""


class IndexBackendError(FramekoError):
    """Raised for index backend failures."""