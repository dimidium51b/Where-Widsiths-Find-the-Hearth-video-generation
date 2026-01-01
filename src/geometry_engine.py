import numpy as np

'''

Module for generating 3D orbital geometries based on musical input.
Status: We see orbits on the video, but the mapping from MIDI to orbit parameters is a bit "weak".
TODO for the next video: Debug some of the data we are generating in this module and 
amplify the midi influence on the orbit parameters.

'''

class OrbitalGeometry:
    def __init__(self, base_radius=5.0):
        self.base_radius = base_radius

    def note_to_radius(self, note: int) -> float:
        # Centering around middle C (60) for musically sensible radii
        normalized = (note - 60) / 60.0
        multiplier = max(0.2, 1.0 + normalized)
        return self.base_radius * multiplier

    def velocity_to_thickness(self, velocity: int) -> float:
        return max(0.5, min(8.0, (velocity / 127.0) * 8.0))

    def velocity_to_glow(self, velocity: int) -> float:
        return (velocity / 127.0) * 1.5

    def generate_3d_orbit(self, event, audio_intensity=0.0):
        note = event['note']
        vel = event['velocity']
        pitch_factor = note / 127.0
        radius = self.note_to_radius(note) * (1.0 + audio_intensity * 0.1)
        thickness = self.velocity_to_thickness(vel) * (1.0 + audio_intensity * 0.05)
        glow = self.velocity_to_glow(vel) * (1.0 + audio_intensity * 0.2)
        z_depth = np.sin(pitch_factor * 2 * np.pi) * (vel / 127.0) * 0.5
        return {
            'radius': float(radius),
            'z_depth': float(z_depth),
            'thickness': float(thickness),
            'glow': float(glow),
            'pitch_weight': float(pitch_factor)
        }