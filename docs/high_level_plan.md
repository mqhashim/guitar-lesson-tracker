# Guitar Practice Assistant — Features → Language

_Per-feature Requirements + feature-correctness Testing criteria live in `feature_specs.md`._
_User-facing journeys (browse forest, add a drill, run a drill, review history) live in `user_workflows.md`._
_Detailed practice mode recipes and per-mode code-test strategies live in `practice_modes.md`._
_Context, locked decisions, and rejected alternatives (read first if you're new to the project) live in `decisions.md`._

## Stage 1 — Foundation (CLI/library)

| Feature | Description | Language | Libraries |
|---|---|---|---|
| DAG topic tracker | Forest of topic nodes (multiple disconnected DAGs). A node may carry a `drill_ref` + `completion_criterion` (e.g. min tempo / min density on that drill); when the engine reports a milestone that satisfies the criterion the node completes and its unlock edges fire. Non-drill nodes (concept anchors like "funk chords/rhythms") complete via manual user toggle. Same unlock semantics either way. Honest-user model. | Python | `networkx`, `json` (stdlib) |
| Practice library | Reference data store of reusable musical content: chord voicings, scale shapes/positions, chord progressions, spider / cross-string / picking patterns. Entries are **timing-agnostic** — store ordered items only, where each item is either a note `{string, fret}` or a rest `{rest: true}`, with optional `length` (default `1`) as a *relative* multiplier in units of the drill's `item_duration`. Drills cite an entry via `library_ref` and supply `item_duration` (16th / 8th / 8th_triplet / quarter / half / whole / bar); engine combines `item_duration × length × slot_width` to materialise a concrete `pattern` at drill-load. | Python | `pyyaml` |
| Drill engine | Define exercises (notes-or-library-ref + tempo + density + progression strategy) and run sessions. Owns: three progression strategies (sequential / coupled / independent), per-drill advancement unit (bar / N bars / full repetition), M-clean-units ramp trigger, drop-back-one failure response, click-with-rhythm vs click-against-pulse modes, warmup flag, the random-syncopation pattern generator with full constraint authoring, library_ref resolution at drill-load, and the no-play idle-unit gate (units with zero detected onsets are neither clean nor dirty — engine keeps clicking, no advance, no regress). Emits per-milestone events the DAG observer consumes. | Python | `pyyaml` (drill files), `random` (stdlib) |
| Metronome | Click track. Owns the click pattern as a sequence of subdivision slots (8th / 16th / 8th-triplet), each tagged accented / normal / muted. Three density levels — pattern, all subdivisions, pulse only — selectable per drill. Doesn't know about syncopation as a concept; it just plays the slot pattern it's given. | Python | `sounddevice` |
| Strum/onset detection | Detect a strum/beat from the input signal. No note identification needed. | Python | `numpy`, optionally `aubio` |
| Audio feedback channel | Score user input against the drill's expected pattern across multiple dimensions: onset timing, note/chord duration, transition gap timing, articulation match (derived from pattern durations), and mute discipline. Per-dimension tolerances scale to subdivision width. Delivers feedback in one of three modes per drill: per-pulse-click pitch encoding (high = rushed, low = lagged), bar-end aural summary, or post-session only. | Python | `aubio` (onset + envelope), `librosa` (spectral envelope for articulation) |
| Per-drill progress tracking | Per-(drill, density, session) full history. Records tempo, accuracy, warmup flag, progression strategy used. Surfaces fastest clean tempo per density level and progression-strategy telemetry (which strategy yielded faster gains over time). | Python | `sqlite3` (stdlib) |
| CLI | Drive every feature from the command line. No GUI required to use the tool. | Python | `argparse` (stdlib) or `click` |

## Stage 1.25 — Terminal shell

| Feature | Description | Language | Libraries |
|---|---|---|---|
| TUI app | Terminal shell over the same core library. Tab view only — engraved staff isn't viable in a terminal. Includes the playhead. | Python | `Textual` |

## Stage 1.5 — Desktop shell

| Feature | Description | Language | Libraries |
|---|---|---|---|
| GUI app | Desktop shell over the same core library. | Python | `PySide6` |
| Tab view renderer | Render a drill's tab notation with the playhead. | Python | `PySide6` (`QGraphicsScene`) |
| Staff view renderer | Render a drill's staff notation with the playhead. Used when the goal is to train staff-reading speed. | Python | `PySide6`, **Bravura** SMuFL font, `music21` (theory primitives) |
| Two-line viewport + playhead | Show current line + next line at most. Hard swap when playhead exits current. Single-line drills loop the playhead. Clock-driven, doesn't wait for the player. | Python | — (composes the renderers above) |

## Stage 2 — Audio hot-loop port

| Feature | Description | Language | Libraries |
|---|---|---|---|
| Audio callback + ring buffer | Real-time audio thread that moves samples between PortAudio buffers and a lock-free ring buffer. Removes GC-induced jitter risk. | Rust | `cpal` (audio I/O), `ringbuf`, `pyo3` + `maturin` (Python binding) |
| Onset detection inner loop | Strum onset detection running on the audio thread, fed from the ring buffer. | Rust | `ndarray` (or just `std`) |
| Everything above the ring buffer | Drill engine, metronome scheduling, stats, UI — unchanged. | Python | (unchanged from Stage 1) |

## Stage 3 — Song practice

| Feature | Description | Language | Libraries |
|---|---|---|---|
| Source separation | Extract guitar stem and non-guitar backing track from an uploaded song. CPU-only friendly. | Python orchestration | **Demucs** (subprocess or library) |
| Guitar transcription | Convert the guitar stem to MIDI notes. | Python orchestration | **Basic Pitch** |
| Tab generation / acceptance | Generate guitar tab from transcribed notes, or accept user-provided tab when generation is wrong. | Python | `music21` |
| Song practice mode | Play the non-guitar backing track at chosen tempo, monitor user's guitar input, apply the existing audio-feedback channel. | Python | (reuses Stage 1 + Stage 2 audio engine) |
| Render songs in viewport | Use the existing two-line viewport to display the song's tab/staff with the playhead. | Python | (reuses Stage 1.5 renderers) |

## Stage 3.5 — Optional

| Feature | Description | Language | Libraries |
|---|---|---|---|
| ML models hosted directly | Run Demucs and Basic Pitch via ONNX inside the Rust process. Drops the Python ML dependency. | Rust | `ort` (ONNX runtime for Rust) |

---

## Transition triggers

**Python → Rust (Stage 2)** happens when one of these lands:

- Measured audio-thread jitter exceeds ~5 ms on real hardware during a real session.
- Background work (transcription run, large stats query) causes audio dropouts.
- Drill workload reaches 32nd-notes-at-fast-tempo territory (~30–50 ms event spacing).
- You decide the Rust learning chunk is worth doing on its own merit.

**Stage 3 → Stage 3.5** is purely opt-in — only if you want to drop the Python ML dependency or pursue the ONNX/Rust path as its own learning track.

---

## Net language list

- **Python** — every stage, every feature, except the audio hot-loop from Stage 2 onward.
- **Rust** — audio callback + onset inner loop (Stage 2); optionally ML hosting (Stage 3.5).
- Nothing else.
