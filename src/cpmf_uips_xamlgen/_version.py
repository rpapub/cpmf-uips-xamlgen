"""NuGet version parsing and comparison utilities."""

NuGetVersion = tuple[int, ...]


def parse_nuget_version(version_str: str) -> NuGetVersion:
    """Parse a NuGet version string into a tuple of integers.

    '25.10.11' -> (25, 10, 11). Supports 3- or 4-segment versions.
    Raises ValueError if the string is not a valid NuGet version.
    """
    parts = version_str.split(".")
    if len(parts) < 3:
        raise ValueError(
            f"Invalid NuGet version {version_str!r}: expected at least 3 segments."
        )
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        raise ValueError(
            f"Invalid NuGet version {version_str!r}: all segments must be integers."
        )


def format_nuget_version(version: NuGetVersion) -> str:
    """Inverse of parse_nuget_version: (25, 10, 11) -> '25.10.11'."""
    return ".".join(str(p) for p in version)
