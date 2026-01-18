import math
import glob
import os
import logging
from manim import tempconfig
from src.data_parser import MusicDNA
from src.renderer import PegasiBMonitor
from src.ffmpeg_utils import combine_partial_list
from src.logging_setup import setup_logging

# Configure logging (creates timestamped log file)
LOG_FILE = setup_logging()
logger = logging.getLogger(__name__)

SEGMENT_LENGTH = 10 * 60  # 10 minutes default
#SEGMENT_LENGTH = 64 * 60  # 10 minutes default



def render_chunk(start_time, end_time, chunk_id, events, all_events):
    chunk_events = [e for e in events if start_time <= e['time'] < end_time]
    logger.info("Rendering chunk %d: %.1f -> %.1f (events=%d)", chunk_id, start_time, end_time, len(chunk_events))
    config = {
        "quality": "high_quality",
        "pixel_height": 2160,
        "pixel_width": 3840,
        "frame_rate": 30,
        "output_file": f"chunk_{chunk_id}",
        "disable_caching": True
    }
    with tempconfig(config):
        scene = PegasiBMonitor(midi_events=chunk_events, midi_stream=all_events, start_t=start_time, duration=(end_time-start_time))
        try:
            scene.render()
            logger.info("Chunk %d rendered (attempt completed)", chunk_id)
        except Exception:
            logger.exception("Chunk %d render failed", chunk_id)
            raise
        finally:
            logger.info("Finished render attempt for chunk %d (%.1f-%.1f)", chunk_id, start_time, end_time)
            # We intentionally avoid automatic ffmpeg concatenation here
            # to keep renders deterministic and retry-safe. Use combine helpers manually later.


if __name__ == "__main__":
    logger.info("Phase 1: Parsing MIDI data")
    dna = MusicDNA("Dimidiums_Orbit_1.mid", "Dimidiums_Orbit_1_v2.wav")
    events = dna.get_midi_events()
    duration = dna.get_duration()

    # Export audit payload for 'No AI' provenance
    try:
        fp = dna.save_audit('audit_events.json')
        logger.info("Audit written: audit_events.json (fingerprint: %s)", fp)
    except Exception:
        logger.exception("Warning: failed to write audit file")

    num_chunks = math.ceil(duration / SEGMENT_LENGTH) if duration > 0 else 0

    logger.info("Total duration: %.1f s -> chunks=%d", duration, num_chunks)
    for i in range(num_chunks):
        s = i * SEGMENT_LENGTH
        e = min(duration, (i + 1) * SEGMENT_LENGTH)
        render_chunk(s, e, i, events, events)

    logger.info("Done - see generated media files in Manim's output folders")
