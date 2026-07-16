#!/usr/bin/env python3
"""Conditionally convert, inspect, and sample demo video media."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 120.0
TRUSTED_PACKAGE_MANAGER_ROOTS = (pathlib.Path("/opt/homebrew"),)


class MediaError(RuntimeError):
    """Raised when a requested media operation cannot be completed."""


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def enclosing_worktree(path: pathlib.Path) -> pathlib.Path | None:
    current = path.absolute()
    if not current.is_dir():
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate
    return None


def executable(name: str) -> str:
    value = shutil.which(name)
    if not value:
        raise MediaError(f"{name} is not available")
    selected = pathlib.Path(os.path.abspath(value))
    try:
        resolved = selected.resolve(strict=True)
    except OSError as exc:
        raise MediaError(f"cannot safely resolve {name}: {selected}") from exc
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise MediaError(f"{name} is not an executable file: {resolved}")

    cwd_worktree = enclosing_worktree(pathlib.Path.cwd())
    candidate_worktrees = {
        root
        for root in (enclosing_worktree(selected), enclosing_worktree(resolved))
        if root is not None
    }
    if cwd_worktree is not None and any(
        is_within(candidate, cwd_worktree) for candidate in (selected, resolved)
    ):
        raise MediaError(f"refusing repository-controlled {name}: {selected}")
    trusted_package_manager = any(
        all(
            is_within(candidate.resolve(), root.resolve())
            for candidate in (selected, resolved)
        )
        and all(
            worktree.resolve() == root.resolve() for worktree in candidate_worktrees
        )
        for root in TRUSTED_PACKAGE_MANAGER_ROOTS
    )
    if candidate_worktrees and not trusted_package_manager:
        raise MediaError(f"refusing {name} from a Git worktree: {selected}")
    return str(resolved)


def available(name: str) -> bool:
    try:
        executable(name)
    except (MediaError, OSError):
        return False
    return True


def existing(path: str) -> pathlib.Path:
    value = pathlib.Path(path).resolve()
    if not value.is_file() or value.stat().st_size == 0:
        raise MediaError(f"input is missing or empty: {value}")
    return value


def media_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if key.upper() != "FFREPORT"
    }


def run(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=media_environment(),
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaError(
            f"media command timed out after {timeout_seconds:g} seconds"
        ) from exc
    if result.returncode:
        raise MediaError("media command failed; inspect the tool locally for details")
    return result


def create_only_output(path: str, suffixes: set[str]) -> pathlib.Path:
    output = pathlib.Path(os.path.abspath(os.path.expanduser(path)))
    if output.suffix.lower() not in suffixes:
        choices = ", ".join(sorted(suffixes))
        raise MediaError(f"output must use one of: {choices}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise MediaError(f"output already exists; refusing overwrite: {output}")
    return output


def temporary_output(output: pathlib.Path) -> pathlib.Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{output.stem}.", suffix=output.suffix, dir=output.parent
    )
    os.close(descriptor)
    return pathlib.Path(name)


def install_create_only(temporary: pathlib.Path, output: pathlib.Path) -> None:
    try:
        os.link(temporary, output, follow_symlinks=False)
    except FileExistsError as exc:
        raise MediaError(
            f"output appeared during render; refusing overwrite: {output}"
        ) from exc
    except OSError as exc:
        raise MediaError("could not atomically install validated media output") from exc


def validate_image(path: pathlib.Path, suffix: str) -> None:
    with path.open("rb") as source:
        header = source.read(12)
    valid = (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        if suffix == ".png"
        else header.startswith(b"\xff\xd8")
    )
    if not valid:
        raise MediaError("rendered contact sheet has an invalid image signature")


def inspect_media(
    path: pathlib.Path, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> dict[str, Any]:
    command = [
        executable("ffprobe"),
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    result = run(command, timeout_seconds)
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe returned invalid JSON") from exc
    streams = raw.get("streams", [])
    video: dict[str, Any] = next(
        (item for item in streams if item.get("codec_type") == "video"), {}
    )
    format_data = raw.get("format", {})
    duration_raw = video.get("duration") or format_data.get("duration") or 0
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError):
        duration = 0.0
    return {
        "path": str(path),
        "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "container": format_data.get("format_name", ""),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "has_video": bool(video),
        "codec": video.get("codec_name", ""),
        "pixel_format": video.get("pix_fmt", ""),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "frame_rate": video.get("avg_frame_rate", ""),
        "duration_seconds": duration,
    }


def convert(
    input_path: str,
    output_path: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    source = existing(input_path)
    output = create_only_output(output_path, {".mp4"})
    temporary = temporary_output(output)
    command = [
        executable("ffmpeg"),
        "-y",
        "-i",
        str(source),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(temporary),
    ]
    try:
        run(command, timeout_seconds)
        existing(str(temporary))
        metadata = inspect_media(temporary, timeout_seconds)
        if not (
            metadata["has_video"]
            and metadata["duration_seconds"] > 0
            and metadata["width"] > 0
            and metadata["height"] > 0
        ):
            raise MediaError("rendered MP4 lacks a valid video stream")
        install_create_only(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"status": "PASS", "command": command, "output": str(output)}


def contact_sheet(
    input_path: str,
    output_path: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    source = existing(input_path)
    output = create_only_output(output_path, {".jpeg", ".jpg", ".png"})
    metadata = inspect_media(source, timeout_seconds)
    duration = float(metadata["duration_seconds"])
    if duration <= 0:
        raise MediaError("cannot sample a zero-duration video")
    interval = max(duration / 12.0, 0.1)
    filter_value = f"fps=1/{interval:.3f},scale=320:-1,tile=4x3"
    temporary = temporary_output(output)
    command = [
        executable("ffmpeg"),
        "-y",
        "-i",
        str(source),
        "-vf",
        filter_value,
        "-frames:v",
        "1",
        str(temporary),
    ]
    try:
        run(command, timeout_seconds)
        existing(str(temporary))
        validate_image(temporary, output.suffix.lower())
        install_create_only(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"status": "PASS", "command": command, "output": str(output)}


def positive_timeout(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return parsed


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    subparsers.add_parser("capabilities")
    for name in ("convert", "contact-sheet"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--input", required=True)
        sub.add_argument("--output", required=True)
        sub.add_argument(
            "--timeout-seconds", type=positive_timeout, default=DEFAULT_TIMEOUT_SECONDS
        )
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--input", required=True)
    inspect_parser.add_argument(
        "--timeout-seconds", type=positive_timeout, default=DEFAULT_TIMEOUT_SECONDS
    )
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        if args.operation == "capabilities":
            result: dict[str, Any] = {
                "ffmpeg": available("ffmpeg"),
                "ffprobe": available("ffprobe"),
            }
        elif args.operation == "convert":
            result = convert(args.input, args.output, args.timeout_seconds)
        elif args.operation == "inspect":
            result = inspect_media(existing(args.input), args.timeout_seconds)
        else:
            result = contact_sheet(args.input, args.output, args.timeout_seconds)
    except (MediaError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
