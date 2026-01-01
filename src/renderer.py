
'''

This is my first Manim project. And I think this is much too complicated for beeing the 
first project. So many things are not working as expected, but I think this is ok for now.
THis will be the first video and we will improve this over the next videos. 

I think it is important that the video is genrerated with kind of "classical rendering" and
not by a diffusion model. THis is importnat, I think. 

'''



import os
import numpy as np
import logging

# I really do not like this * import, but it is done in all the Manim examples, 
# so until we understand this better, we do it like this as well
from manim import *

from .geometry_engine import OrbitalGeometry

from manim import ValueTracker, linear

# module logger
logger = logging.getLogger(__name__)

# Color helpers

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    r, g, b = rgb
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))


def _lerp_color(a_hex, b_hex, t: float):
    ar, ag, ab = _hex_to_rgb(a_hex)
    br, bg, bb = _hex_to_rgb(b_hex)
    rr = ar + (br - ar) * t
    rg = ag + (bg - ag) * t
    rb = ab + (bb - ab) * t
    return _rgb_to_hex((rr, rg, rb))

# This is an object inherited from Manim 
# After youhave undertodd it, this is very straightforward
# I think I only understood this, while most of the code was already written
# So please do not blame me and do not take this as an example of good Manim code


class PegasiBMonitor(ThreeDScene):
    def __init__(self, midi_events=None, midi_stream=None, audio_envelope=None, start_t=0.0, duration=10.0, max_ships=15, max_trails=1200, trail_spawn_interval=0.25, **kwargs):
        """midi_events: events for this chunk (geometry)
           midi_stream: full event stream used for HUD (if None, falls back to midi_events)
           max_ships: max number of ship objects to create (limits GPU/CPU work)
           max_trails: maximum number of trail dots to keep in memory (recycles oldest)
           trail_spawn_interval: default seconds between trail dots for each ship
        """
        super().__init__(**kwargs)
        self.midi_events = midi_events or []
        self.midi_stream = midi_stream if midi_stream is not None else (midi_events or [])
        self.audio_envelope = audio_envelope or []  # list of (time, rms)
        self.start_t = start_t
        self.duration = duration
        self.max_ships = max_ships
        self.max_trails = max_trails
        self.trail_spawn_interval = trail_spawn_interval
        # small pool for recycled trail dots
        self._trail_pool = []

    # TODO: why do we not see this? Debug for next video
    def _sample_audio(self, t: float) -> float:
        """Return normalized audio intensity in [0,1] at time t using linear interpolation."""
        if not self.audio_envelope:
            return 0.0
        times = np.array([p[0] for p in self.audio_envelope])
        vals = np.array([p[1] for p in self.audio_envelope])
        # If all zeros or invalid, return 0
        if not vals.any():
            return 0.0
        # Normalize by max to get [0,1]
        maxv = vals.max()
        if maxv <= 0:
            return 0.0
        interp = np.interp(t, times, vals)
        return float(interp / maxv)

    # Here happens all the shit
    # we are painting the Dimidium planet and some ships orbiting around it
    # This is not so bad, but lacks music visualisation in the moment
    # Wahtever, release early, realease often, next one will be better, I hope
    # We are writing some static text here as well, like the band logo and so on
    def construct(self):
        engine = OrbitalGeometry()
        PHOSPHOR_GREEN = "#00A896"
        self.camera.background_color = "#0D0D0D"

        axes = ThreeDAxes(axis_config={"stroke_width": 1, "color": BLUE_E}, tips=False)
        self.add(axes)

        # Planet: Dimidium as a simple 3D blue sphere at origin
        # Use a geometric Sphere instead of a 2D SVG texture for now
        try:
            planet = Sphere(radius=0.8, resolution=(30, 30))
            planet.set_color("#2a6fda")
            planet.move_to([0, 0, 0])
            planet._last_angle = 0.0

            def _planet_updater(m):
                cur = time_tracker.get_value()
                target = cur * 0.02  # very slow rotation rate (radians)
                delta = target - getattr(m, '_last_angle', 0.0)
                if abs(delta) > 1e-6:
                    m.rotate(delta, axis=OUT)
                    m._last_angle = target

            planet.add_updater(_planet_updater)
            self.add(planet)
        except Exception:
            # Fallback to a 2D circle if Sphere isn't available in this Manim build
            planet = Circle(radius=1.6, color="#2a6fda", fill_opacity=1.0)
            planet.move_to([0, 0, 0])
            self.add(planet)

        # Band icon (prefer PNG, then SVG, then fallback) — place small in fixed upper-left corner
        icon_candidates = [
            os.path.join(os.getcwd(), 'assets', 'band_icon.png'),
            os.path.join(os.getcwd(), 'assets', 'band_icon.svg'),
            os.path.join(os.getcwd(), 'media', 'images', 'band_icon.png'),
            os.path.join(os.getcwd(), 'media', 'images', 'band_icon.svg'),
        ]
        fixed_icon = None
        for p in icon_candidates:
            if os.path.exists(p):
                try:
                    if p.lower().endswith('.svg'):
                        fixed_icon = SVGMobject(p)
                    else:
                        fixed_icon = ImageMobject(p)
                except Exception:
                    try:
                        fixed_icon = ImageMobject(p)
                    except Exception:
                        fixed_icon = None
                break

        if fixed_icon is not None:
            # scale small and put into fixed frame at UL
            fixed_icon.scale(0.12)
            fixed_icon.to_corner(UL).shift(RIGHT * 0.18 + DOWN * 0.12)
            # Use fixed-in-frame so it doesn't move with camera
            self.add_fixed_in_frame_mobjects(fixed_icon)
        else:
            # fallback: small circle in fixed frame
            placeholder = Circle(radius=0.12, color=PHOSPHOR_GREEN, fill_opacity=0.8)
            placeholder.to_corner(UL).shift(RIGHT * 0.18 + DOWN * 0.12)
            self.add_fixed_in_frame_mobjects(placeholder)

        # Time tracker drives animations and ticker
        time_tracker = ValueTracker(0.0)

        logger.info("Constructing scene: start_t=%.3f duration=%.3f events=%d", self.start_t, self.duration, len(self.midi_events))

        # Persistent watermark (use full PRD tagline)
        watermark = Text("Human Soul. Digital Craft. No AI Music. Proven.", font="Courier New", font_size=14, color=GREY_B).to_corner(UR)
        self.add_fixed_in_frame_mobjects(watermark)

        # Bottom-right: Band name and Title
        # Hardcodec title. Great. #TODO for next video: make this configurable on main as parameter.
        # But for now, I just want to finish this  

        title_text = Text("Lanthorn of Tellus", font="Courier New", font_size=16, color=WHITE).to_corner(DR).shift(LEFT*0.18+UP*0.12)
        band_text = Text("In Dimidium's Orbit", font="Courier New", font_size=12, color=GREY_B).next_to(title_text, DOWN, aligned_edge=RIGHT).shift(LEFT*0.02)
        self.add_fixed_in_frame_mobjects(title_text, band_text)

        # MIDI HUD: show only a single fixed variable (current selected note) using an Integer
        # This avoids re-creating Text objects and prevents layout/glyph reflow artifacts hopefully.
        hud_state = {'last_sec': -1}

        # MIDI HUD: three-event display (fixed) with note+velocity and TIME to avoid reflow ( has been a fucking problem and was hard to solve this way)
        hud_state = {'last_sec': -1}

        hud_label = Text("MIDI-DATA:", font="Courier New", font_size=12, color=PHOSPHOR_GREEN).to_corner(DL).shift(UP*0.18 + RIGHT*0.12)
        ev0 = Text("N--- V---", font="Courier New", font_size=12, color=PHOSPHOR_GREEN).next_to(hud_label, RIGHT, buff=0.28)
        ev1 = Text("N--- V---", font="Courier New", font_size=12, color=PHOSPHOR_GREEN).next_to(ev0, RIGHT, buff=0.18)
        ev2 = Text("N--- V---", font="Courier New", font_size=12, color=PHOSPHOR_GREEN).next_to(ev1, RIGHT, buff=0.18)
        time_text = Text("TIME -> 00:00:00", font="Courier New", font_size=12, color=PHOSPHOR_GREEN).next_to(ev2, RIGHT, buff=0.40)

        # background rect sized conservatively; we'll update it each second to avoid fucking artifacts from whereever
        hud_bg = Rectangle(width=4.2, height=0.40, fill_opacity=0.12, fill_color=BLACK, stroke_opacity=0).move_to(hud_label.get_center())
        self.add_fixed_in_frame_mobjects(hud_bg, hud_label, ev0, ev1, ev2, time_text)

        def _format_hms(sec_float):
            s = int(round(sec_float))
            h = s // 3600
            m = (s % 3600) // 60
            s = s % 60
            return f"{h:02d}:{m:02d}:{s:02d}"

        # Really? I think this is not how Manim wants us to do this 
        def hud_multi_updater(mob):
            cur = time_tracker.get_value()
            sec = int(cur)
            if sec == hud_state['last_sec']:
                return
            hud_state['last_sec'] = sec

            # Choose the next upcoming event index (or fallback to last past index)
            next_idx = None
            for idx, ev in enumerate(self.midi_stream):
                if ev['time'] >= cur:
                    next_idx = idx
                    break
            if next_idx is None:
                for idx in range(len(self.midi_stream) - 1, -1, -1):
                    if self.midi_stream[idx]['time'] <= cur:
                        next_idx = idx
                        break

            # Build display parts and update Text objects in-place (preserve positions, for you know these stupid artifacts)
            parts = []
            for offset in range(3):
                idx = (next_idx + offset) if next_idx is not None else None
                if idx is not None and 0 <= idx < len(self.midi_stream):
                    e = self.midi_stream[idx]
                    parts.append(f"N{e['note']:03d} V{e['velocity']:03d}")
                else:
                    parts.append("N--- V---")

            now_str = _format_hms(cur)

            # Update each event text (preserve anchored screen centers to avoid reflow artifacts)
            try:
                new0 = Text(parts[0], font="Courier New", font_size=12, color=PHOSPHOR_GREEN)
                new0.move_to(ev0.get_center())
                ev0.become(new0)
            except Exception:
                pass
            try:
                new1 = Text(parts[1], font="Courier New", font_size=12, color=PHOSPHOR_GREEN)
                new1.move_to(ev1.get_center())
                ev1.become(new1)
            except Exception:
                pass
            try:
                new2 = Text(parts[2], font="Courier New", font_size=12, color=PHOSPHOR_GREEN)
                new2.move_to(ev2.get_center())
                ev2.become(new2)
            except Exception:
                pass

            try:
                newt = Text(f"TIME -> {now_str}", font="Courier New", font_size=12, color=PHOSPHOR_GREEN)
                newt.move_to(time_text.get_center())
                time_text.become(newt)
            except Exception:
                pass

            # Update background to snugly fit the current text extents
            try:
                left = hud_label.get_left()[0]
                right = time_text.get_right()[0]
                width = max(1.8, float(right - left) + 0.4)
                new_bg = Rectangle(width=width, height=hud_label.height + 0.24, fill_opacity=0.10, fill_color=BLACK, stroke_opacity=0).move_to(hud_label.get_center() + (time_text.get_center() - hud_label.get_center())*0.5)
                hud_bg.become(new_bg)
            except Exception:
                pass

        # attach a single updater to the label (keeps updater cleanup simple, I hope)
        hud_label.add_updater(hud_multi_updater)

        #### To be honest, this orbit thing does not work 100 % as intended yet. 
        #### But whatever, this is fine for the first video. For the next one, we can improve it, I hope.


        # Create orbit objects that respond to time_tracker using updaters
        orbits = []
        import collections
        # Trail management: keep a deque of transient trail dots to fade and recycle
        if not hasattr(self, '_trail_items'):
            self._trail_items = collections.deque()
        if not hasattr(self, '_trail_pool'):
            self._trail_pool = collections.deque()
        trail_life = 8.0  # seconds each trail dot remains and fades (configurable)
        trail_spawn_interval = max(0.02, self.trail_spawn_interval)  # seconds between trail dots (sparser)

        # Performance logging state
        perf_state = {'last_perf_sec': -1}

        def _trail_manager(_):
            now = time_tracker.get_value()

            # periodic perf logging (every 10 s)
            if int(now) % 10 == 0 and int(now) != perf_state['last_perf_sec']:
                perf_state['last_perf_sec'] = int(now)
                logger.info(f"PERF t={now:.1f}s trails={len(self._trail_items)} pool={len(self._trail_pool)} mobjects={len(self.mobjects)}")

            # Fade existing trail items and recycle old ones without removing from scene
            for _ in range(len(self._trail_items)):
                t = self._trail_items[0]
                age = now - getattr(t, '_created_at', now)
                if age >= trail_life:
                    try:
                        # retire to pool (hide and move offscreen) to avoid expensive scene.add/remove
                        t.set_opacity(0.0)
                        t.move_to([0, 0, -9999])
                        self._trail_items.popleft()
                        # only keep pool up to max_trails
                        if len(self._trail_pool) < self.max_trails:
                            self._trail_pool.append(t)
                        else:
                            # pool full; permanently drop by removing from scene
                            try:
                                self.remove(t)
                            except Exception:
                                pass
                    except Exception:
                        try:
                            self._trail_items.popleft()
                        except Exception:
                            pass
                else:
                    # Fade: linearly reduce opacity over trail_life
                    t.set_opacity(max(0.0, 1.0 - age / trail_life) * 0.9)
                    # rotate queue left to iterate without modifying length
                    self._trail_items.rotate(-1)

        self.add_updater(_trail_manager)

        # Limit ships to keep this not looking like a traffic jam in space or so :-)
        ships_to_create = min(self.max_ships, len(self.midi_events))
        logger.info("Generating %d ships (max_ships=%d)" , ships_to_create, self.max_ships)
        for idx, ev in enumerate(self.midi_events[:ships_to_create]):
            if idx % 10 == 0:
                logger.debug("Generating orbit %d/%d time=%.3f note=%s", idx, ships_to_create, ev.get('time'), ev.get('note'))
            orbit_data = engine.generate_3d_orbit(ev, audio_intensity=0.2)

            # Faint orbital ring for context
            orbit_ring = Circle(radius=orbit_data['radius'], color=PHOSPHOR_GREEN, stroke_width=1, stroke_opacity=0.10)
            orbit_ring.move_to([0, 0, orbit_data['z_depth']])
            self.add(orbit_ring)

            # spaceship dot that will travel along the orbit when time comes
            # color & parameters vary per event so ships have distinct orbits (NOT WORKIN FOR NOW, but let us have in mind that this is our goal)
            pw = orbit_data.get('pitch_weight', 0.5)
            vel = ev.get('velocity', 64)

            # base colors by pitch band
            # !!!! TODO: fix ship color logic later for next video
            if pw < 0.33:
                base_color = "#6C9EFF"
            elif pw < 0.66:
                base_color = PHOSPHOR_GREEN
            else:
                base_color = "#FFD166"

            # ship
            ship_radius_base = max(0.08, 0.06 * (0.8 + vel / 127.0))
            ship = Dot(radius=ship_radius_base, color=base_color)
            
            # place initially at center. Can we do this more elegant ??? TODO: for next video
            ship.move_to([0, 0, orbit_data['z_depth']])
            ship.set_opacity(0.0)

            ev_time = ev['time']
            ship._ev_time = ev_time
            ship._orbit_radius = orbit_data['radius']
            ship._z_depth = orbit_data['z_depth']

            # much slower base speed and slight variation by velocity and pitch (TODO: make this work for next video)
            base_speed = 0.08  # radians per second (slow)
            ship._speed = base_speed * (0.5 + (vel / 127.0) * 0.6) * (1.0 - pw * 0.4)

            # phase spread to avoid all ships starting at same position
            ship._initial_phase = ((ev.get('note', 60) % 12) / 12.0) * TAU
            
            # small orbital inclination based on pitch (±20 deg) TODO: make this logarithmic to see any effetc?? next video
            ship._inclination = (pw - 0.5) * np.deg2rad(40.0)
            ship._last_trail = -1.0

            def make_ship_updater(s):
                def updater(mm):
                    cur = time_tracker.get_value()
                    dt = cur - mm._ev_time
                    if dt < 0:
                        mm.set_opacity(0.0)
                        return

                    # sample audio intensity to influence color & size (I DO NOT SEE THIS, so a  TODO)
                    intensity = self._sample_audio(cur)

                    # blend base color with white based on intensity
                    col = _lerp_color(base_color, "#FFFFFF", min(1.0, 0.2 + 0.8 * intensity))
                    mm.set_color(col)

                    # size scaling (small) with intensity
                    mm.set_width(ship_radius_base * (1.0 + 0.6 * intensity))

                    # ship visibility + fade: remain visible for a long time, then fade slowly
                    # Very elegant, but only half working
                    ship_visible_secs = 15.0
                    ship_fade_secs = 8.0
                    if dt <= ship_visible_secs:
                        ship_op = 1.0
                    elif dt <= ship_visible_secs + ship_fade_secs:
                        ship_op = max(0.0, 1.0 - (dt - ship_visible_secs) / ship_fade_secs)
                    else:
                        ship_op = 0.0
                    mm.set_opacity(ship_op)

                    # compute angular position along orbit
                    angle = mm._initial_phase + dt * mm._speed
                    r = mm._orbit_radius
                    incl = mm._inclination

                    x = r * np.cos(angle)
                    y = r * np.sin(angle) * np.cos(incl)
                    z = mm._z_depth + r * np.sin(angle) * np.sin(incl)
                    mm.move_to([x, y, z])

                    # leave a trail dot every ~trail_spawn_interval seconds
                    # THis is working better than exspected, but TODO can we get more resolution here??
                    if dt - mm._last_trail >= trail_spawn_interval:
                        mm._last_trail = dt
                        # recycle oldest trail dot if pool limit reached
                        if len(self._trail_items) + len(self._trail_pool) >= self.max_trails:
                            # reuse the oldest existing trail (rotate left) if present
                            if self._trail_items:
                                old = self._trail_items.popleft()
                                old.move_to([x, y, z])
                                old._created_at = cur
                                old.set_opacity(0.9)
                                self._trail_items.append(old)
                            elif self._trail_pool:
                                old = self._trail_pool.popleft()
                                old.move_to([x, y, z])
                                old._created_at = cur
                                old.set_opacity(0.9)
                                # pool items are already in scene; reuse directly
                                self._trail_items.append(old)
                        else:
                            # create a new trail dot (rare once under cap)
                            dot = Dot(radius=0.02, color=col)
                            dot.move_to([x, y, z])
                            dot.set_opacity(0.9)
                            dot._created_at = cur
                            self.add(dot)
                            self._trail_items.append(dot)
                return updater

            ship.add_updater(make_ship_updater(ship))
            # make ships slightly bigger
            ship.set_width(ship_radius_base * 1.6)
            self.add(ship)
            orbits.append(orbit_ring)
            orbits.append(ship)

        # Camera and ambient rotation
        # Working very nice, this is what the framework was made for, I think
        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        self.begin_ambient_camera_rotation(rate=0.005)

        # Animate global time tracker from 0 to duration (this drives updaters)
        # The run_time equals the scene's duration to produce a time-accurate render
        logger.info("Starting animation run_time=%.3f seconds", self.duration)
        try:
            self.play(time_tracker.animate.set_value(self.duration), run_time=self.duration, rate_func=linear)
            logger.info("Animation finished")
        except Exception:
            logger.exception("Animation failed or timed out; falling back to direct set")
            # In environments where real-time playing may fail (very short durations), fallback to direct set
            time_tracker.set_value(self.duration)

        # Clean up updaters after the run to prevent surprises in repeated renders
        try:
            hud_label.remove_updater(hud_multi_updater)
        except Exception:
            pass
        for o in orbits:
            try:
                if o.updaters:
                    o.remove_updater(o.updaters[0])
            except Exception:
                pass

        logger.info("Scene complete: mobjects=%d", len(self.mobjects))