# Feature Specs — Requirements & Testing

Per-feature **Requirements** (responsibilities / constraints / what must be
true of the implementation) and **Testing criteria** for feature
correctness. Distinct from `practice_modes.md`, which carries per-mode
drill-engine tests; this file is about each *feature* being correct on its
own terms.

Keyed by the feature names in `high_level_plan.md`. Read that file first
for the descriptive overview; come here for the implementation contract.

User-facing journeys (`user_workflows.md`) are mapped to specific feature
Requirements bullets via the **Implements workflow** notation, so each
journey has a concrete implementation owner.

---

## Stage 1 — Foundation

### DAG topic tracker

**Requirements**:

- Data model is a **forest** (multiple disconnected DAGs), not a single
  DAG. Code paths must handle N root nodes per forest file.
- Each node carries: `id`, `title`, optional `drill_ref`, optional
  `completion_criterion`, optional `description`, and outgoing `unlocks`
  edges (list of node IDs).
- `completion_criterion` for drill-bearing nodes is a structured threshold:
  `{min_tempo?, min_density?, min_subdivision?, min_item_duration?, phase?}`.
  A node trips when a drill milestone event satisfies *all* present fields.
  `min_item_duration` lets a node observe an item_duration ramp milestone
  (e.g. "Drill A reached 16th-note items").
- **Multiple nodes can reference the same `drill_ref`** with different
  criteria (e.g. "Drill A at 70 BPM" and "Drill A at 100 BPM 16th notes"
  are two distinct nodes both observing the same long-lived drill).
- Drill-bearing nodes complete only via engine-emitted milestone events.
  No manual override on these.
- Non-drill nodes (`drill_ref` absent) complete via **manual user toggle**.
  The honest-user model applies — no validation, no anti-cheat.
- Locked/unlocked/completed status is computed from completion state +
  inbound unlock edges, not stored redundantly.
- Persistence format is hand-editable JSON (the user authors the forest).
- Subscribes to drill milestone events from the Per-drill progress
  tracking feature; updates node completion when criteria are satisfied.
- **Implements workflow**: *Browse the forest*, *Focus a lesson* (renders
  the forest with completion / unlock status, surfaces node details and
  downstream unlocks, exposes manual-complete toggle for non-drill nodes).

**Testing criteria**:

- Load → serialize → load round-trips identically for a hand-authored
  forest fixture.
- Computed unlock state matches expected for a fixture with mixed
  completed / locked / unlocked-untouched nodes.
- Drill milestone event matching `completion_criterion` trips the right
  node and only the right node; a near-miss event (e.g. tempo one step
  below threshold) does not trip it.
- Two nodes referencing the same drill at different criteria trip
  independently as milestones cross each threshold.
- Manual toggle on a non-drill node fires its unlock edges; manual toggle
  rejected on a drill-bearing node (engine-only path).
- Cycle detection at load — a forest file with a cycle is rejected with a
  clear error pointing at the offending nodes.

---

### Practice library

**Requirements**:

- Library entries are YAML files keyed by stable, dotted IDs (e.g.
  `scales.d_major.position_5`, `chords.open.c_major`,
  `progressions.i_vi_iv_v.key_c`, `patterns.spider.4_finger`).
- Entry types at minimum: `chord`, `scale`, `chord_progression`, `pattern`.
- Entries are **timing-agnostic**: store note identity and ordering only.
  **No** `duration` (in absolute terms), `slot`, `marker`, `subdivision`,
  or `tempo` fields on library entries.
- Each ordered item is either a **note** `{string, fret, length?}` or a
  **rest** `{rest: true, length?}`. `length` (int, default `1`) is a
  *relative* multiplier — it stays dimensionless until the drill provides
  `item_duration`, at which point the engine derives absolute slot extent
  as `item_duration × length × slot_width`.
- `chord` entries: `{strings: [{string, fret}, ...]}` — all played
  simultaneously. (Sustains on a chord are expressed via the drill's
  `item_duration` and per-occurrence `length` when the chord is cited
  inside a progression.)
- `scale` entries: ordered list of notes / rests as defined above.
- `chord_progression` entries: ordered list of chord references (entry IDs
  resolving to `chord` entries), each optionally carrying `length` and
  with `rest` entries allowed between chords.
- `pattern` entries (spider / cross-string / picking shapes): ordered list
  of notes / rests as defined above.
- Drill citation: `library_ref: <id>` + drill-side `item_duration` (fixed),
  or `start_item_duration` + `item_duration_steps` (ramping). Engine
  resolves `library_ref + (current) item_duration + subdivision + per-item
  length` to the same `pattern: [{slot, string, fret, duration, marker},
  ...]` shape an inline `pattern` produces. Rests become slot gaps.
  Downstream components (metronome, renderer, scorer) see no difference
  between inline and resolved patterns.
- Optional drill-side `marker_overlay` applies accent / mute markers at
  specific resolved-pattern indices.
- Unknown `library_ref` → drill rejected at load with a clear error.
- Unsatisfiable resolution (e.g. progression with `item_duration: bar`
  expanded over a 1-bar drill that doesn't fit the progression length)
  rejected at load.
- Library is UI-agnostic — no rendering, tempo, feedback, or drill-engine
  concerns leak into entries.

**Testing criteria**:

- Each entry round-trips load → serialize → load identically on fixtures
  for every entry type.
- Same entry + different `(item_duration, subdivision)` pairs produce
  different valid resolved patterns; resolved-pattern shape matches what
  an equivalent inline `pattern` would produce.
- Items with `length > 1` produce sustained notes spanning the expected
  number of slots; items with `rest: true` produce slot gaps; combinations
  (rest with `length: 3`) produce multi-slot rests.
- Resolution is deterministic — same inputs always produce the same
  resolved pattern.
- Unknown `library_ref` raises a clear, file-pointing error at drill load.
- `marker_overlay` indices map to the correct slots in the resolved
  pattern; out-of-range indices rejected at load.
- Chord-progression resolution: each chord reference resolves transitively
  to its `chord` entry's strings; unknown sub-ref rejected.

---

### Drill engine

**Requirements**:

- Owns the three progression strategies (`sequential`, `coupled`,
  `independent`) per `practice_modes.md`.
- Owns the three ramp axes: **tempo**, **density**, and **item_duration**.
  `independent` advances exactly one axis (declared via `progression_axis`);
  `coupled` rotates through an ordered `coupled_axes` subset;
  `sequential` is tempo+density only — item_duration ramping under
  `sequential` is intentionally not supported (compose via separate drills).
- For item_duration ramping: walks `item_duration_steps` left-to-right on
  advance, right-to-left on regression. Cannot step below
  `item_duration_steps[0]` or above the last element.
- Validates at drill-load: `item_duration` is mutually exclusive with
  `(start_item_duration, item_duration_steps)`; `start_item_duration ==
  item_duration_steps[0]` when ramping; `subdivision` is at least as fine
  as the finest value in `item_duration_steps`.
- Owns advancement-unit counting (`n_bars: N` or `full_repetition`).
- Owns the M-clean-units ramp trigger and the per-axis drop-back-one
  regression action.
- Owns the **no-play idle-unit gate**: a unit with zero detected player
  onsets is treated as idle — no advance, no regress, click continues. The
  scorer scores any onsets it sees; the gate is enforced by the engine
  before applying the verdict.
- Owns the warmup prompt (`Y/n`) and the expedited ramp mechanics from
  `practice_modes.md`'s Session start section.
- Owns the random-syncopation generator and validates `generator_constraints`
  at drill load (contradictory constraints rejected).
- Resolves `library_ref` + `item_duration` to a concrete `pattern` at
  drill-load via the Practice library. Inline `pattern` and resolved
  patterns are indistinguishable downstream.
- Emits **milestone events** as the session progresses — at minimum:
  ramp-completed (`{drill_id, axis, new_tempo, new_density, subdivision,
  item_duration, phase}`) — for the DAG topic tracker to consume.
  `axis` ∈ `{tempo, density, item_duration}` indicates which axis just
  advanced.
- Writes per-(drill, density, session) records to the Per-drill progress
  tracking store.
- **Implements workflow**: *Add a drill* (auto-discovers drill YAML files
  from the drills directory; validates at load; surfaces clear errors with
  file + reason; no manual ingestion step), *Run a drill* (launches by
  drill ID or path; warmup prompt; session loop; idle-unit gate; ramp /
  regression).

**Testing criteria**:

- Drill YAML with `pattern` xor `library_ref` parses; both present or
  neither present rejected at load.
- Engine rejects `item_duration`, `marker_overlay`, `start_item_duration`,
  and `item_duration_steps` when `pattern` is inline (these are
  library_ref-only fields).
- Engine rejects drills that supply both `item_duration` and
  `(start_item_duration, item_duration_steps)`.
- `progression_axis: item_duration` with `item_duration_steps: [quarter,
  8th, 16th]` — feeding M clean reps advances steps in order; an extra M
  clean reps after the last step is a no-op (capped at list end).
- `progression_axis: item_duration` regression — dirty rep drops one step
  left in `item_duration_steps`; dirty rep at `item_duration_steps[0]` is
  a no-op.
- `coupled_axes: [tempo, density, item_duration]` rotates ramps in declared
  order: each clean M advances the next axis, wraps after the third.
- Synthetic input stream with zero onsets across an advancement unit →
  engine reports idle, M-counter unchanged, no regression fired, click
  continues uninterrupted.
- Synthetic input stream with one onset that fails the scorer → engine
  evaluates as dirty, fires regression on the last-advanced axis.
- Milestone events match the spec shape and fire exactly once per ramp.
- Drill-load discovery: dropping a new YAML in the drills directory
  surfaces it on next session list without manual ingestion.
- Drill-load errors point at file path and line/field that failed
  validation.

---

### Metronome

**Requirements**:

- Click pattern is a sequence of subdivision slots, each tagged
  `accented` / `normal` / `muted`.
- Three density levels: `1` = pattern (drill notes only), `2` = all
  subdivisions, `3` = pulse only.
- Density is selected per drill (and changes during the session as the
  engine progresses density).
- Subdivisions supported: `8th`, `16th`, `8th_triplet`. No 32nds, no
  16th-triplets (per `decisions.md`).
- Stays on a straight grid in `click_against_pulse` mode regardless of
  pattern content.
- Doesn't know about syncopation as a concept — it plays the slot pattern
  it's handed.
- Click audio is short, low-jitter, and uses distinct timbres for
  accented vs normal slots.

**Testing criteria**:

- Density 1: clicks fire only at slots with a drill note.
- Density 2: clicks fire at every subdivision slot.
- Density 3: clicks fire only at pulse (beat) slots.
- `click_with_rhythm` vs `click_against_pulse`: pattern slot timings vs
  straight grid timings as expected.
- Slot timing jitter measured against the audio clock stays within the
  PipeWire quantum budget (~2.6 ms at 128 frames @ 48 kHz).

---

### Strum/onset detection

**Requirements**:

- Detects strum / pick onsets in the input signal. No pitch / note
  identification at Stage 1–2.
- Operates per-buffer (PortAudio callback granularity) with sub-buffer
  onset timestamp accuracy.
- Stays a pure DSP module — takes audio samples in, emits onset events
  out. No knowledge of advancement units, drill schedule, or scoring
  decisions.
- Handles both built-in mic and direct-in / interface input equivalently
  (PipeWire abstracts this).

**Testing criteria**:

- Fixture WAVs with hand-verified onset times: detector reports times
  within an established ms tolerance (set during development against
  ground truth).
- Synthetic silence buffer → zero onsets reported.
- False-positive rate on amp hum / room noise fixtures is below a chosen
  threshold.
- Latency from onset in samples to onset event emitted is bounded by the
  buffer size.

---

### Audio feedback channel

**Requirements**:

- Scores user input across five dimensions per `practice_modes.md`:
  onset timing, note/chord duration, transition gap timing, articulation
  match (derived from pattern durations), mute discipline.
- Each scalar tolerance is a percentage of the slot width — tolerances
  scale with tempo (same percentage → tighter ms tolerance at faster
  tempos).
- Three feedback modes per drill: `per_pulse_click` (next click pitch
  encodes accuracy — high = rushed, low = lagged), `bar_end_summary`,
  `post_session`.
- Does not gate advance / regress — it only reports scoring verdicts.
  The drill engine owns the idle-unit gate and the application of
  verdicts.

**Testing criteria**:

- Each tolerance computation: `tolerance_pct` * `slot_width_ms` produces
  the expected ms tolerance across tempos and subdivisions.
- Per-pulse-click feedback: rushed input → higher pitch; lagged input →
  lower pitch; clean input → reference pitch.
- Bar-end summary aggregates dimension verdicts correctly over a bar.
- Post-session summary produces the same numbers as the running aggregate
  for an identical session replay.

---

### Per-drill progress tracking

**Requirements**:

- Per-(drill, density, item_duration, session) records: start time,
  end time, tempo reached, density reached, item_duration reached,
  progression strategy used, warmup flag, per-dimension accuracy
  aggregates.
- Computes derived stats: fastest clean tempo per `(density,
  item_duration)` per drill (captures both the internalization gap and the
  subdivision-density gap), progression-strategy telemetry (gains over
  time by strategy).
- Emits milestone events the DAG topic tracker subscribes to (e.g.
  ramp-completed with the new tempo/density/subdivision).
- Schema migrations are forward-compatible — adding a field should not
  break old records.
- **Implements workflow**: *Review past sessions* (per-drill history:
  fastest clean tempo per density, strategy used, tempo curve over time).

**Testing criteria**:

- All sessions are recorded — warmup or not (warmup is a starting flag,
  not a tracking gate, per `decisions.md`).
- Fastest-clean-tempo query returns the highest clean-completed tempo per
  `(density, item_duration)` pair.
- Milestone events fire exactly once per ramp; consumers can rely on at-
  least-once and at-most-once.
- Round-trip: write session record → read → identical fields.

---

### CLI

**Requirements**:

- Every Stage 1 feature reachable from the CLI without a GUI.
- Subcommands cover at minimum: list drills, run a drill, list forest /
  topic, mark a non-drill node complete, show session history.
- Errors are surfaced with the failing file + reason (matches the drill-
  engine load-error guarantee).
- **Implements workflow**: *Browse the forest*, *Focus a lesson*, *Add a
  drill*, *Run a drill*, *Review past sessions* — all five must have a
  CLI entrypoint.

**Testing criteria**:

- Each subcommand has a smoke test that invokes it against a fixture
  drills/forest dir.
- `--help` documents every subcommand and option.
- Exit codes: 0 on success, non-zero on validated user error, distinct
  non-zero on engine/internal error.

---

## Stage 1.25 — Terminal shell

### TUI app

**Requirements**:

- Built on Textual; consumes the same core library the CLI uses.
- Tab view only — staff engraving isn't viable in a terminal.
- Renders the playhead (clock-driven, doesn't wait for the player — per
  `decisions.md`).
- Two-line viewport: current line + next line at most. Single-line drills
  loop the playhead.
- **Implements workflow**: *Browse the forest*, *Focus a lesson*, *Run a
  drill*, *Review past sessions*. *Add a drill* stays a file-drop op
  outside the TUI.

**Testing criteria**:

- Snapshot test of forest view, focus view, session view, history view on
  a fixture.
- Playhead position advances on a clock signal independent of any input.
- Two-line swap fires when the playhead exits the current line.

---

## Stage 1.5 — Desktop shell

### GUI app

**Requirements**:

- Built on PySide6; consumes the same core library.
- **Implements workflow**: *Browse the forest*, *Focus a lesson*, *Run a
  drill*, *Review past sessions*. *Add a drill* is a file-drop op (a
  GUI authoring tool is out of scope for Stage 1 per `decisions.md`).

**Testing criteria**:

- Smoke test launches the app against a fixture data dir without
  crashing.
- Each workflow has a top-level navigation entry.

### Tab view renderer

**Requirements**:

- Renders the drill's tab notation with the playhead.
- Custom `QGraphicsScene` (no Verovio — per `decisions.md`).

**Testing criteria**:

- Snapshot test of a known drill's tab rendering at a fixed viewport
  size.
- Playhead position is derivable from the engine clock at any moment.

### Staff view renderer

**Requirements**:

- Renders the drill's staff notation with the playhead, using the Bravura
  SMuFL font.
- Used when the goal is to train staff-reading speed.
- Tab XOR staff per drill — never stacked.

**Testing criteria**:

- Snapshot test of a known drill's staff rendering at a fixed viewport
  size.
- Glyph alignment against Bravura metrics is correct on a fixture.

### Two-line viewport + playhead

**Requirements**:

- Shows current line + next line at most. Hard swap when playhead exits
  current.
- Single-line drills loop the playhead.
- Clock-driven; never waits for the player.
- Composes the Tab and Staff renderers above.

**Testing criteria**:

- Swap fires at the right clock tick for a fixture drill.
- Single-line drill: playhead returns to start cleanly each loop.
- Multi-line drill: viewport never shows more than two lines.

---

## Stage 2 — Audio hot-loop port

### Audio callback + ring buffer (Rust)

**Requirements**:

- Audio callback (cpal) only moves samples between PortAudio buffers and
  a lock-free ring buffer. No drill / scoring / Python state touched on
  the audio thread.
- Ring buffer is single-producer / single-consumer; overrun/underrun
  behaviour is well-defined and observable.
- Exposes a Python binding (pyo3 + maturin) the Stage 1 Python engine
  consumes without changes above the binding.

**Testing criteria**:

- Audio thread never blocks on Python state (verified by simulated GIL
  contention).
- Ring buffer never underruns under simulated load with the
  Stage-1-equivalent producer rate.
- Callback latency stays under the established jitter budget (~5 ms per
  `high_level_plan.md`'s transition trigger).

### Onset detection inner loop (Rust)

**Requirements**:

- Runs on the audio thread, consuming samples from the ring buffer.
- Emits onset events to the Python side via a non-blocking channel.
- Behaviourally indistinguishable from the Python `aubio` reference on the
  fixture set used to validate Stage 1 detection.

**Testing criteria**:

- A/B against the Python reference on the same fixture WAVs: onset times
  match within an established tolerance.
- No allocations on the audio thread under steady-state operation.

---

## Stage 3 — Song practice

### Source separation

**Requirements**:

- Extracts guitar stem and non-guitar backing track from an uploaded
  song.
- CPU-only friendly (Demucs CPU variants).
- Runs as a subprocess; doesn't block the audio engine.

**Testing criteria**:

- Smoke test on a fixture mix: separation runs to completion, outputs
  two stems.
- Subprocess crash leaves the engine in a recoverable state.

### Guitar transcription

**Requirements**:

- Converts the guitar stem to MIDI notes via Basic Pitch.
- CPU-only friendly. Runs as a subprocess.

**Testing criteria**:

- Smoke test on a fixture stem: transcription runs to completion,
  produces a MIDI file.
- Subprocess error surfaces a clear user-facing reason.

### Tab generation / acceptance

**Requirements**:

- Generates guitar tab from transcribed MIDI notes (music21 + a fret-
  position solver).
- Accepts user-provided tab when generation is wrong.
- (Stage 3 open question per `decisions.md`: the actual MIDI-to-fret-
  position solver is unsolved.)

**Testing criteria**:

- Round-trip: known MIDI → generated tab → re-parsed → semantic match
  with original on fixtures the solver is known to handle.
- User-provided tab override path produces the same internal pattern
  shape as a generated one.

### Song practice mode

**Requirements**:

- Plays the non-guitar backing track at the chosen tempo, monitors user's
  guitar input, applies the existing audio-feedback channel.
- Reuses the Stage 1 + Stage 2 audio engine — no separate audio path.

**Testing criteria**:

- Smoke test runs a fixture song end-to-end with a scripted clean player.
- Feedback channel verdicts match the same drill engine's behaviour on
  equivalent timing fixtures.

### Render songs in viewport

**Requirements**:

- Uses the existing two-line viewport to display song tab/staff with the
  playhead.
- Reuses Stage 1.5 renderers — no separate rendering path.

**Testing criteria**:

- Snapshot test of a fixture song's first 4 bars renders correctly.

---

## Stage 3.5 — Optional

### ML models hosted directly (Rust + ONNX)

**Requirements**:

- Runs Demucs and Basic Pitch via ONNX inside the Rust process.
- Drops the Python ML dependency.
- Behaviourally indistinguishable from the subprocess path on the
  validation fixtures.

**Testing criteria**:

- A/B output against the Stage 3 subprocess path on fixture inputs.
- No process spawns at runtime.
