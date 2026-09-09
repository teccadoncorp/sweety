# Social Publish

Use this only when a connector is connected and the copy is ready.

## Platforms

- `reddit` — needs `title`, `text`, and `subreddit`
- `twitter` / `x` — `text` ≤ 280 characters
- `linkedin` — longer editorial `text`
- `facebook` — `text`, optional `image_url`
- `instagram` — requires a **public** `image_url` (not localhost)

## Flow

1. `list_connectors`. If the platform is disconnected, write the draft as an artifact and tell the board how to connect it.
2. Call `post_social`. Sweety queues a board approval by default.
3. When the board approves, Sweety posts with the stored tokens.
4. Never invent a post URL.

Instagram cannot pull images from `localhost`. Use a public HTTPS image or skip IG until one exists.
