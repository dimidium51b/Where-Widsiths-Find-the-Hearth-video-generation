'''

We are readding the MIDI and the WAV file here 
for showing the midi data as raw values (working, bottom left in the video).
We hope that makes it transparent, that this is based on midi data and not AI generated.

Idea was as well to visualise the MIDI data in the planetary renderer, with colors and orbit angles.

THis is not so convincing yet, so we keep it for the next video. Hopefully :-)

'''



import logging
import mido
import librosa
import numpy as np

logger = logging.getLogger(__name__)

class MusicDNA:
    """Lightweight music parser """
    def __init__(self, midi_path, wav_path, fps=30):
        self.midi_path = midi_path
        self.wav_path = wav_path
        self.fps = fps
        logger.debug("MusicDNA initialized: midi=%s wav=%s fps=%d", midi_path, wav_path, fps)

    def get_midi_events(self):
        logger.info("Loading MIDI file: %s", self.midi_path)
        mid = mido.MidiFile(self.midi_path)
        events = []
        current_time = 0.0
        for msg in mid:
            current_time += msg.time
            if msg.type == 'note_on' and getattr(msg, 'velocity', 0) > 0:
                events.append({
                    'time': current_time,
                    'note': msg.note,
                    'velocity': msg.velocity,
                })
        logger.info("Extracted %d MIDI events", len(events))
        logger.debug("MIDI event time range: 0 - %.3f", events[-1]['time'] if events else 0.0)
        return events

    def get_audio_envelope(self, sr=None):
        logger.info("Loading audio for envelope: %s", self.wav_path)
        # Use sr=None to preserve file sampling rate where possible
        y, sr = librosa.load(self.wav_path, sr=sr)
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        logger.debug("Audio envelope samples=%d sr=%d", len(rms), sr)
        return list(zip(times, rms))

    def get_duration(self):
        # Prefer explicit metadata, fallback to audio envelope
        midi_len = mido.MidiFile(self.midi_path).length
        audio_len = 0
        try:
            audio_len = librosa.get_duration(filename=self.wav_path)
        except Exception:
            logger.warning("librosa.get_duration failed, falling back to envelope sampling")
            env = self.get_audio_envelope()
            audio_len = env[-1][0] if env else 0
        duration = max(midi_len, audio_len)
        logger.info("Duration: midi=%.3f audio=%.3f selected=%.3f", midi_len, audio_len, duration)
        return duration

    def save_audit(self, path):
        """Save an audit JSON with MIDI events and a SHA256 fingerprint.

        The file includes all extracted events and a fingerprint computed over
        the canonical JSON representation to provide a simple 'No AI' proof artifact.
        """
        import json
        import hashlib
        logger.info("Writing audit to %s", path)
        events = self.get_midi_events()
        payload = {
            'midi_file': self.midi_path,
            'wav_file': self.wav_path,
            'event_count': len(events),
            'events': events
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        fingerprint = hashlib.sha256(canonical).hexdigest()
        payload['fingerprint'] = fingerprint
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        logger.info("Audit written with fingerprint %s", fingerprint)
        return fingerprint
