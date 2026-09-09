# Visual Studio

Use this when a task needs a still or a talking-head video.

## Images

- Call `generate_image` with a concrete prompt: subject, setting, lighting, negative space for type, brand voice.
- Save the returned URL on the task (the tool already stores a media asset).
- Localhost image URLs will not work on Instagram. Prefer the hosted URL the model returns, or a public CDN.

## HeyGen video

- `list_connectors` first. If HeyGen is not connected, ask the board to add `HEYGEN_API_KEY` plus avatar/voice IDs.
- Call `generate_heygen_video` with a short spoken script (30–45 seconds).
- Poll `check_heygen_video` if you need status.

Do not claim a video is published anywhere.
