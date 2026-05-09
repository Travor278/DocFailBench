# Demo GIF Guide

The README can use a short GIF once the review UI and report flow are stable.
Keep it under 20 seconds and under roughly 8 MB if possible.

## Recommended Recording

For a community-facing README GIF, prefer frozen combined public RC artifacts.
Use Stage7 or Stage8 packets only when demonstrating the curation workflow.

Record this flow:

1. Open `data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.md` or the README combined public RC leaderboard.
2. Open an HTML report for a combined public RC rerun if available.
3. Show one table/formula/caption failure with source evidence.
4. Optional curation demo: open `runs/stage7_non_gov_public/review_packet_non_gov_public/review_packet_non_gov_public.html`.

Suggested screen size: 1440x900 or 1600x900.

Use the diagnostic leaderboard only when explicitly showing the older
synthetic-heavy regression set.

## Windows Tools

Easy options:

- ScreenToGif for a compact GIF.
- ShareX for MP4/GIF capture.
- OBS Studio for MP4, then convert with ffmpeg.

## ffmpeg Conversion

If you record `demo.mp4`, convert it to a README-friendly GIF:

```powershell
ffmpeg -i demo.mp4 `
  -vf "fps=12,scale=1280:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" `
  -loop 0 docs/assets/docfailbench_demo.gif
```

For a smaller file:

```powershell
ffmpeg -i demo.mp4 `
  -vf "fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" `
  -loop 0 docs/assets/docfailbench_demo.gif
```

## README Embed

After the GIF exists:

```markdown
![DocFailBench review flow](docs/assets/docfailbench_demo.gif)
```

Avoid committing raw recording files. Commit only the final optimized GIF.
