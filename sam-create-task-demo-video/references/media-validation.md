# Media Validation

The final deliverable must be MP4 unless the user explicitly changes the request.

## Convert

Use a broadly compatible video codec, `yuv420p`, and fast-start metadata. Keep
the raw recording temporary. Do not overwrite the source in place.

## Inspect deterministically

Record:

- Container and MIME type.
- Presence of a video stream.
- Codec, pixel format, width, height, frame rate, and duration.
- File size and SHA-256.
- Conversion command and result.

Reject empty files, missing video streams, zero duration, zero dimensions, and
non-MP4 final artifacts.

## Inspect visually

Play the final file. Generate a contact sheet spanning the complete duration.
Confirm the initial state, actions, proof moment, final state, readable pacing,
and absence of secrets or private data. A metadata-only check does not prove the
demo content or privacy.

The helper invokes `ffmpeg` or `ffprobe` only for the requested media operation.
Its `capabilities` command and the package harness do not require either tool.
