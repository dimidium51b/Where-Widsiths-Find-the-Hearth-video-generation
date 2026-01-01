import logging
import subprocess
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


def stitch_chunks(chunk_paths: Iterable[str], wav_path: str, output: str = "final_pillar_video.mp4", concat_path: str = "chunks.txt"):
    """Create a concat file for ffmpeg and run the stitch command.

    This function writes a concat file listing the given chunk_paths (one per line
    in the format required by ffmpeg's concat demuxer) and runs ffmpeg to merge
    video chunks with the provided audio.
    """
    concat_file = Path(concat_path)
    logger.info("Writing concat file %s for %d chunks", concat_file, len(list(chunk_paths)))
    with concat_file.open('w') as f:
        for p in chunk_paths:
            f.write(f"file '{p}'\n")

    cmd = f"ffmpeg -f concat -safe 0 -i {concat_file} -i {wav_path} -c copy -map 0:v -map 1:a {output}"
    try:
        logger.info("Running ffmpeg stitch: %s", cmd)
        subprocess.run(cmd, shell=True, check=True)
        logger.info("stitch_chunks completed: %s", output)
    except subprocess.CalledProcessError as exc:
        logger.exception("ffmpeg stitch failed")
        raise
    return cmd


def combine_partial_list(list_path: str, output: str):
    """Combine partial movies listed by a Manim-generated partial movie list.

    Fixes a common issue where entries contain "file:/abs/path" URIs and
    converts them to paths accepted by ffmpeg's concat demuxer.
    """
    lp = Path(list_path)
    if not lp.exists():
        raise FileNotFoundError(list_path)
    fixed = lp.parent / (lp.stem + "_fixed.txt")
    logger.info("Fixing partial list %s -> %s", lp, fixed)
    with lp.open('r') as inf, fixed.open('w') as outf:
        for line in inf:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # expected format: file '...'
            if line.startswith("file '") and line.endswith("'"):
                inner = line[6:-1]
                # strip file: scheme if present
                if inner.startswith('file:'):
                    inner = inner[5:]
                outf.write(f"file '{inner}'\n")
            else:
                # fallback: write raw
                outf.write(line + "\n")

    cmd = f"ffmpeg -f concat -safe 0 -i {fixed} -c copy {output}"
    try:
        logger.info("Running ffmpeg combine: %s", cmd)
        subprocess.run(cmd, shell=True, check=True)
        logger.info("combine_partial_list completed: %s", output)
    except subprocess.CalledProcessError:
        logger.exception("ffmpeg combine failed")
        raise
    return cmd
