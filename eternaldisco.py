import math

# MIDI setup: ticks per quarter note (time resolution)
TICKS_PER_BEAT = 96  # a common MIDI PPQ value

# Define MIDI channels for instruments (0-15, where 9 is reserved for drums in General MIDI)
CHAN_CLASSICAL = 0   # Strings/piano for classical section
CHAN_REGGAE   = 1   # Organ or guitar for reggae off-beats
CHAN_BASS     = 2   # Bass guitar
CHAN_ROCK     = 4   # Distorted guitar for rock
CHAN_DRUMS    = 9   # Drum channel (GM standard uses channel 10, index 9)

# Program (instrument) numbers for General MIDI (0-127, where 0 = Acoustic Grand Piano)
PROG_STRINGS  = 48   # String Ensemble 1
PROG_ORGAN    = 16   # Drawbar Organ (for reggae skank)
PROG_BASS     = 33   # Electric Bass (finger)
PROG_GUITAR   = 30   # Distortion Guitar

# MIDI note numbers for drum hits (General MIDI Percussion on channel 9)
KICK        = 36  # Bass Drum
SNARE       = 38  # Acoustic Snare
HIHAT_CLOSED= 42  # Closed Hi-Hat
HIHAT_OPEN  = 46  # Open Hi-Hat (not used extensively here)
RIDE_CYMBAL = 51  # Ride Cymbal
CRASH_CYMBAL= 49  # Crash Cymbal
TOM_LOW     = 41  # Low Floor Tom
# (We can use additional toms or percussion as needed)

# Define chord note mappings (MIDI note numbers) for each chord in different arrangements:
# Classical triads (strings) – mid-range voicings
chords_classical = {
    "Am": [57, 60, 64],   # A minor: A3, C4, E4
    "G" : [55, 59, 62],   # G major: G3, B3, D4
    "F" : [53, 57, 60],   # F major: F3, A3, C4
    "E" : [52, 56, 59]    # E major: E3, G#3, B3 (G#3 = 56)
}
# Reggae chords (use similar pitches for consistency; E chord has two versions)
chords_reggae = {
    "Am": chords_classical["Am"],        # A minor
    "G" : chords_classical["G"],         # G major
    "F" : chords_classical["F"],         # F major
    "Em": [52, 55, 59],                  # E minor: E3, G3, B3 (G natural for reggae section)
    "E" : chords_classical["E"]          # E major: E3, G#3, B3 (used at transition)
}
# Rock chords (power chords: root, fifth, octave root)
chords_rock = {
    "Am": [45, 52, 57],   # A5: A2, E3, A3
    "G" : [43, 50, 55],   # G5: G2, D3, G3
    "F" : [41, 48, 53],   # F5: F2, C3, F3
    "E" : [40, 47, 52]    # E5: E2, B2, E3
}
# Bass root notes (very low octave, one note per chord)
bass_notes = {
    "A": [33],  # A1
    "G": [31],  # G1
    "F": [29],  # F1
    "E": [28]   # E1
}

# Helper: convert a time in beats to ticks
def beats_to_ticks(beats):
    return int(beats * TICKS_PER_BEAT)

# Prepare list to collect MIDI events as (time_in_ticks, bytes_data)
events = []

# 1. Add Program Change events for each instrument channel at time 0
events.append((0, bytes([0xC0 | CHAN_CLASSICAL, PROG_STRINGS])))  # classical strings
events.append((0, bytes([0xC0 | CHAN_REGGAE,   PROG_ORGAN])))     # reggae organ
events.append((0, bytes([0xC0 | CHAN_BASS,     PROG_BASS])))      # bass guitar
events.append((0, bytes([0xC0 | CHAN_ROCK,     PROG_GUITAR])))    # distorted guitar
# (No program change needed for CHAN_DRUMS; channel 9 is standard GM drum kit)

# 2. Tempo changes (MIDI Meta events). We add these as FF 51 (Set Tempo).
def add_tempo_change(time_ticks, bpm):
    # microseconds per quarter note = 60,000,000 / BPM
    mpqn = int(60000000 / bpm)
    # Tempo meta event: 0xFF, 0x51, 0x03, followed by 3 bytes of MPQN
    events.append((time_ticks, bytes([
        0xFF, 0x51, 0x03,
        (mpqn >> 16) & 0xFF, (mpqn >> 8) & 0xFF, mpqn & 0xFF
    ])))

# Define section start times in ticks
start_classical = 0
start_reggae    = beats_to_ticks(32)   # after 8 bars of 4 beats (8*4=32 beats) at 90 BPM (tick timeline continues)
start_rock      = start_reggae + beats_to_ticks(32)  # after another 8 bars (32 beats) for reggae

# Tempo changes at section boundaries:
add_tempo_change(0, 90)               # Classical: 90 BPM at time 0
add_tempo_change(start_reggae, 80)    # Reggae: 80 BPM at the start of reggae section (tick 3072)
add_tempo_change(start_rock, 120)     # Rock: 120 BPM at the start of rock section (tick 6144)

# 3. Classical section note events (8 bars, A minor progression repeated twice)
# Progression for 4 bars: Am -> G -> F -> E, then repeat
progression_classical = ["Am", "G", "F", "E"] * 2  # 8 chords (8 measures)
for i, chord_name in enumerate(progression_classical):
    chord_start = start_classical + beats_to_ticks(4 * i)  # each chord lasts 4 beats (one measure)
    notes = chords_classical[chord_name]
    # Note On events for the chord (all notes at once)
    for pitch in notes:
        events.append((chord_start, bytes([0x90 | CHAN_CLASSICAL, pitch, 100])))  # Note On, velocity 100
    # Note Off events at end of measure (chord held for full 4 beats)
    chord_end = chord_start + beats_to_ticks(4)
    for pitch in notes:
        events.append((chord_end, bytes([0x80 | CHAN_CLASSICAL, pitch, 64])))     # Note Off, velocity 64 (release)

# 4. Reggae section note events (8 bars)
# We use the progression: Am, G, F, Em, then Am, G, F, E (to introduce E major in final bar)
progression_reggae = ["Am", "G", "F", "Em",  "Am", "G", "F", "E"]
for i, chord_name in enumerate(progression_reggae):
    bar_start = start_reggae + beats_to_ticks(4 * i)
    # Compute key times within the bar (in ticks)
    beat1 = bar_start + beats_to_ticks(0)      # 0 beats into bar (bar start)
    beat2 = bar_start + beats_to_ticks(1)      # 1 beat into bar
    beat3 = bar_start + beats_to_ticks(2)      # 2 beats into bar
    beat4 = bar_start + beats_to_ticks(3)      # 3 beats into bar
    # Determine if this is the last bar (we will add a fill if so)
    last_bar = (i == len(progression_reggae) - 1)
    # **Bass:** play root on beat 1 and beat 3 (one-drop feel)
    # Use bass note corresponding to chord root (just the first letter, since our keys are A, G, F, E)
    root_letter = chord_name[0]  # e.g. "Am" -> "A"
    if root_letter in bass_notes:
        root_pitch = bass_notes[root_letter][0]
        # Bass note on beat 1
        events.append((beat1, bytes([0x90 | CHAN_BASS, root_pitch, 100])))
        # Bass note off after a short duration (here, 1 beat long to separate notes)
        events.append((beat1 + beats_to_ticks(1), bytes([0x80 | CHAN_BASS, root_pitch, 64])))
        # Bass note on beat 3
        events.append((beat3, bytes([0x90 | CHAN_BASS, root_pitch, 100])))
        events.append((beat3 + beats_to_ticks(1), bytes([0x80 | CHAN_BASS, root_pitch, 64])))
    # **Guitar/Organ skank:** off-beat chords on beats 2 and 4
    chord_notes = chords_reggae[chord_name]  # get the triad for this chord
    # Beat 2 chord stab
    for pitch in chord_notes:
        events.append((beat2, bytes([0x90 | CHAN_REGGAE, pitch, 90])))      # Note On at beat 2
        events.append((beat2 + beats_to_ticks(0.5), bytes([0x80 | CHAN_REGGAE, pitch, 64])))  # Note Off after 1/2 beat
    # Beat 4 chord stab (skip if we are doing a drum fill instead)
    if not last_bar:
        for pitch in chord_notes:
            events.append((beat4, bytes([0x90 | CHAN_REGGAE, pitch, 90])))  # Note On at beat 4
            events.append((beat4 + beats_to_ticks(0.5), bytes([0x80 | CHAN_REGGAE, pitch, 64])))  # Note Off after 1/2 beat
    # **Drums:** one-drop pattern
    # Hi-hat on offbeat 8ths: (i.e., 0.5, 1.5, 2.5, 3.5 beats)
    hi_hat_times = [bar_start + beats_to_ticks(b) for b in [0.5, 1.5, 2.5, 3.5]]
    if last_bar:
        hi_hat_times.pop()  # remove the last offbeat (3.5) to allow space for fill
    for t in hi_hat_times:
        events.append((t, bytes([0x99, HIHAT_CLOSED, 80])))  # closed hat on off-beat
    # One-drop Kick + Snare on beat 3
    events.append((beat3, bytes([0x99, KICK, 100])))
    events.append((beat3, bytes([0x99, SNARE, 100])))
    # **Transition fill on last reggae bar:**
    if last_bar:
        # Drum fill: snare hit on beat 4, low tom on beat 4& (half-beat after beat 4)
        events.append((beat4, bytes([0x99, SNARE, 110])))
        events.append((beat4 + beats_to_ticks(0.5), bytes([0x99, TOM_LOW, 110])))
        # (We will add a crash cymbal on the first beat of the rock section for the final transition)

# 5. Rock/Metal section note events (8 bars)
# Progression: Am, G, F, E repeated twice (8 bars). 
# The pattern intensifies in the second half.
progression_rock = ["Am", "G", "F", "E",  "Am", "G", "F", "E"]
for j, chord_name in enumerate(progression_rock):
    bar_start = start_rock + beats_to_ticks(4 * j)
    beat1 = bar_start
    beat2 = bar_start + beats_to_ticks(1)
    beat3 = bar_start + beats_to_ticks(2)
    beat4 = bar_start + beats_to_ticks(3)
    # Determine if we are in the latter half (for double bass section)
    double_time = (j >= 4)  # bars 5-8 of rock section use double-kick pattern
    # **Rhythm Guitar:** power chord on beat 1 and beat 3
    guitar_notes = chords_rock[chord_name]
    # Strum chord on beat 1
    for pitch in guitar_notes:
        events.append((beat1, bytes([0x90 | CHAN_ROCK, pitch, 120])))
    # Note Off for that chord at beat 3 (so it rings for 2 beats)
    for pitch in guitar_notes:
        events.append((beat3, bytes([0x80 | CHAN_ROCK, pitch, 64])))
    # Strum chord again on beat 3
    for pitch in guitar_notes:
        events.append((beat3, bytes([0x90 | CHAN_ROCK, pitch, 120])))
    # Note Off at end of bar (beat 5 which is next bar's start)
    for pitch in guitar_notes:
        events.append((beat4 + beats_to_ticks(1), bytes([0x80 | CHAN_ROCK, pitch, 64])))
    # **Bass Guitar:** play root notes on every beat (quarter notes)
    root_letter = chord_name[0]  # "Am" -> 'A', "F" -> 'F', etc.
    if root_letter in bass_notes:
        bass_pitch = bass_notes[root_letter][0]
        for b in [beat1, beat2, beat3, beat4]:
            events.append((b, bytes([0x90 | CHAN_BASS, bass_pitch, 100])))
            # Note Off slightly before the next beat to keep it punchy (here ~90% of the beat length)
            events.append((b + int(0.9 * TICKS_PER_BEAT), bytes([0x80 | CHAN_BASS, bass_pitch, 64])))
    # **Drums:** 
    if not double_time:
        # Standard rock beat (basic 4/4 rock groove)
        events.append((beat1, bytes([0x99, KICK, 127])))    # Kick on 1
        events.append((beat2, bytes([0x99, SNARE, 120])))   # Snare on 2
        events.append((beat3, bytes([0x99, KICK, 127])))    # Kick on 3
        events.append((beat4, bytes([0x99, SNARE, 120])))   # Snare on 4
        # Hi-hat every 1/2 beat (8th notes)
        eight_times = [bar_start + beats_to_ticks(x) for x in [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]]
        # If this is the very first rock bar, we will add a crash cymbal on beat1 (so we can omit the hat on beat1 to let the crash ring)
        if j == 0:
            eight_times.remove(bar_start)  # remove 0 (beat1) from hat times, as crash will be there
        for t in eight_times:
            events.append((t, bytes([0x99, HIHAT_CLOSED, 90])))
    else:
        # Double-time metal beat (thrash style)
        # **Double Bass**: kick drum on every 16th note subdivision (4 per beat = 16 per bar)
        t = bar_start
        step = beats_to_ticks(0.25)  # 16th note = 0.25 beat
        while t < bar_start + beats_to_ticks(4):
            events.append((t, bytes([0x99, KICK, 127])))
            t += step
        # **Snare**: on 2 and 4 as usual (can coincide with some kicks, adding power)
        events.append((beat2, bytes([0x99, SNARE, 120])))
        events.append((beat4, bytes([0x99, SNARE, 120])))
        # **Ride Cymbal**: to cut through, play ride on each quarter note beat
        events.append((beat1, bytes([0x99, RIDE_CYMBAL, 100])))
        events.append((beat2, bytes([0x99, RIDE_CYMBAL, 100])))
        events.append((beat3, bytes([0x99, RIDE_CYMBAL, 100])))
        events.append((beat4, bytes([0x99, RIDE_CYMBAL, 100])))
        # (The ride hits often coincide with snare on 2,4 which is common in metal drumming)

# Add the transition Crash cymbal on the first beat of the rock section (to mark the genre switch)
events.append((start_rock, bytes([0x99, CRASH_CYMBAL, 127])))

# 6. End-of-track meta event
end_time = start_rock + beats_to_ticks(32)  # end of 8 rock bars (should be tick 9216)
events.append((end_time, bytes([0xFF, 0x2F, 0x00])))  # End of Track

# Sort events by time to ensure correct order
events.sort(key=lambda e: e[0])

# Assemble MIDI binary data from events
midi_bytes = bytearray()
last_time = 0
for time, data in events:
    # Calculate delta-time (time since last event) in ticks
    delta = time - last_time
    # Variable-length encoding for delta
    # (Most significant bit in each byte indicates if another byte follows)
    to_write = []
    # Build bytes in reverse order
    buffer = delta & 0x7F
    to_write.append(buffer)
    delta >>= 7
    while delta:
        buffer = (delta & 0x7F) | 0x80
        to_write.insert(0, buffer)
        delta >>= 7
    # Append delta bytes
    for b in to_write:
        midi_bytes.append(b)
    # Append event bytes
    midi_bytes.extend(data)
    last_time = time

# Wrap track data with MIDI header and track header
# MIDI Header: 6 bytes payload
header = bytearray(b"MThd") 
header.extend((6).to_bytes(4, 'big'))             # header length
header.extend((0).to_bytes(2, 'big'))             # format 0 (single track)
header.extend((1).to_bytes(2, 'big'))             # number of tracks = 1
header.extend((TICKS_PER_BEAT).to_bytes(2, 'big'))# time division (ticks per beat)
# Track Chunk:
track_chunk = bytearray(b"MTrk")
track_chunk.extend(len(midi_bytes).to_bytes(4, 'big'))

# Combine header, track chunk header, and track data
midi_data = header + track_chunk + midi_bytes

# Write the MIDI data to a file
with open("genre_blend.mid", "wb") as f:
    f.write(midi_data)

print("MIDI file 'genre_blend.mid' has been generated. You can now open it in a MIDI player or DAW.")
