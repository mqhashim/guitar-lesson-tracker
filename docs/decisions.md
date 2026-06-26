# Decisions & Rationale

Context, locked decisions, rejected alternatives, and the reasoning a new
agent (or future-you) would need to avoid re-litigating settled calls.

Read this *before* proposing changes to `high_level_plan.md` or
`practice_modes.md`. If you'd push back on a decision here, check the
rejected-alternative column first.

---

## Deployment context

| | |
|---|---|
| Host OS | Fedora Kinoite (atomic). Root filesystem is read-only; software installs via `rpm-ostree` (layered, requires reboot) or user-space tools (`~/.local/`, Flatpak, Distrobox). |
| Target packaging | Flatpak. Sandboxed. KDE Plasma 6 frontend. |
| Audio layer | PipeWire. Quantum 128 @ 48 kHz delivers ~2.6 ms granularity, well inside this project's timing budget. |
| GUI integration target | KDE (Konsole for TUI, native Qt for GUI). |
| Dev environment | Distrobox `dev` container holds the build toolchain; host stays clean. See sibling repos `MQH_linux_setup/` for the Kinoite + dev environment setup. |

## User profile

- Solo developer, building this for personal practice. Open-sourceable, but not designed for general distribution.
- Guitar player; the tool's job is to support their own practice routine.
- Honest-user model — no anti-cheat, no input validation against gaming the stats.
- Project doubles as a **Rust learning track** — Stage 2 (audio hot-loop port) is committed, not optional, for that reason as much as for any performance need.

---

## Locked decisions

Each row: the decision, what was rejected, why it was rejected.

### Stack & language

| Decision | Rejected alternative | Why |
|---|---|---|
| Python as primary; Rust for Stage 2 hot-loop only | Rust-first / Rust-only | Python + `sounddevice` comfortably handles 16ths @ 120 BPM (the realistic ceiling for human practice). Rust ports the audio callback for jitter guarantees + as the Rust learning chunk. |
| Stage 2 Rust port is committed | "Optional, if profiling demands" | User wants the Rust learning track regardless. The boundary (ring buffer) is drawn so the port is a swap-in, not a rewrite. |
| Python single-language until Stage 2 | Mixed-language from day one | Getting to a working tool fast matters. Rust comes when there's a known-correct Python reference to A/B against. |
| No Go, no Zig, no JavaScript/TypeScript | Adding any of them as a backend or glue language | Python covers everything Go would; Rust covers everything Zig would; PySide6 covers what JS would for GUI. |
| PySide6 (GUI) + Textual (TUI) | Tauri, Electron, local web app | Tauri drags JS/TS in. Electron is heavyweight. Local web app + Flatpak is awkward. PySide6 stays in-language and has a clean Flatpak BaseApp. |

### Architecture

| Decision | Rejected alternative | Why |
|---|---|---|
| Library-first: `core/` is UI-agnostic; TUI + GUI are thin shells | Build GUI-first, factor library later | Lets TUI and GUI share the same engine. Lets Stage 2 swap the audio implementation without touching UI. |
| "Audio thread is dumb": PortAudio callback only moves samples between buffers and a lock-free ring buffer | Do detection / scheduling inside the callback in Python | Keeps Python GIL/GC off the critical path. Makes Stage 2 Rust port a swap-in, not a rewrite. Composes naturally with PortAudio/PipeWire callback model. |
| Two-line viewport for notation rendering | Songsterr-style whole-piece engraving | We only ever show 2 lines at a time. Verovio's strengths (system breaks, full-page layout) don't apply. |
| Custom `QGraphicsScene` rendering with Bravura font | Verovio (C++ engraving engine with Python bindings) | Two-line viewport doesn't need a layout engine. QGraphicsScene gives more cursor control and a smaller dep footprint. Bravura is the SMuFL-standard music font (MIT-licensed). |
| Tab XOR staff per drill | Songsterr-style stacked notation + tab | User picks one view per drill. Stacked is more rendering work for no training benefit when focusing on one view. |
| Cursor is pure clock math, doesn't wait for player | Karaoke-mode cursor that pauses on errors | Follow-the-bouncing-ball. If you stop playing, the cursor keeps going. Pausing is an explicit action. |

### Audio / DSP

| Decision | Rejected alternative | Why |
|---|---|---|
| Strum / onset detection only (Stage 1–2); pitch detection deferred to Stage 3 | Polyphonic pitch detection from day one | Beat/strum detection is sufficient for rhythm and timing drills. Pitch detection is a different DSP class and is needed only for the future quiz-me modes. |
| Audio feedback (next click's pitch encodes accuracy) over live visual feedback | Live visual mistake highlighting | 80–150 ms human visual reaction floor makes live visual feedback functionally useless. Audio sidesteps the reaction-time problem. |
| Metronome owns the click pattern; drill engine owns the expected user pattern | Single combined "rhythm" concept | Separation enables both click-with-rhythm and click-against-pulse modes from the same engine with the same drill definition. |
| Subdivisions: 8th, 16th, 8th triplet | 16th triplets / 32nds / arbitrary tuplets | Covers rock/pop/funk/swing/shuffle/12-8. Faster subdivisions hit the onset-detection floor (~30–50 ms event spacing). |
| Audio interface choice unspecified; PipeWire handles whatever's there | Require a specific USB interface | This is a personal tool; user picks their hardware. PipeWire at quantum 128 handles built-in mic or USB interface equivalently. |

### Drill engine semantics

| Decision | Rejected alternative | Why |
|---|---|---|
| Three density steps: pattern / all subdivisions / pulse only | 4 steps (add no-click), 5 steps (gradually remove pulse), continuous fade | 3 maps cleanly to "training wheels on / training wheels off / pulse only." Continuous fade is harder to mark "density level passed." |
| Drill picks its progression strategy (sequential / coupled / independent) | Locked single strategy across all drills | Different drill types need different progression behavior. Speed drills want independent; internalization wants sequential; balanced wants coupled. |
| Per-(drill, density, session) stats granularity | One-tempo-per-drill aggregate | Captures the internalization gap — your fastest tempo at density 1 can be much higher than at density 3; that delta is the practice signal. |
| Single regression action (drop back one step on last-advanced axis); configurable trigger sensitivity | Per-drill regression actions (multi-step drops, drill restart, etc.) | Single action is simpler to reason about and test. Trigger sensitivity gives flexibility without complicating the action. |
| Warmup = starting-parameter behavior, prompted at session start | `warmup_eligible` flag that excludes sessions from stats | All sessions count. Warmup is about where you *start* (expedited ramp from base) vs *continue* (one step below previous best). |
| Advancement unit: `n_bars: N` or `full_repetition` | Separate `bar` as a third option | `n_bars: 1` is equivalent to `bar`. Smaller schema, fewer code paths. |
| Scoring across 5 dimensions (onset, duration, transition gap, articulation match, mute discipline) with per-dimension tolerances | Single `clean_tolerance_pct` covering everything | Different dimensions need independently-tunable strictness. Articulation is derived from pattern durations, so no extra schema field. |
| Random-syncopation drills don't preserve the bar | Reproducible bars via seed | The bar itself doesn't matter for that drill type — only response speed to fresh patterns. |
| Drill engine owns the no-play idle-unit gate | Scorer owns it / onset detector owns it | Engine already owns advancement/regression policy; the "should we evaluate?" decision lives next to "what do we do with the verdict?" Onset detector stays pure DSP (no knowledge of advancement units); scorer scores what it sees; engine reads "any onset this unit?" and gates ramp/regression on it. |
| Practice library is a pure reference data store; entries are timing-agnostic | Library entries are DAG nodes / library entries carry duration & timing | DAG drill-node completion already answers "did I clear this content?"; library-level tracking is redundant given one-drill-per-scale-position authoring. Timing lives on the drill so the same scale shape can be used at quarters for slow internalization and at 16ths for speed work without duplicating data. Drill cites entries via `library_ref` + `item_duration`; engine combines with `subdivision` to materialise the concrete pattern. Item shape: note `{string, fret, length?}` or rest `{rest: true, length?}`; `length` is a relative multiplier (in units of `item_duration`, default 1) for sustains and multi-slot rests. Stays timing-agnostic — `length` is dimensionless until the drill provides `item_duration`. |
| `item_duration` is a first-class progression axis alongside tempo and density | Subdivision ramp as a separate strategy / extending the `density` enum to cover note-value steps | Same advancement / regression mechanics already exist on tempo and density — a third axis fits cleanly under `independent` (`progression_axis: item_duration`) and `coupled` (opt-in via `coupled_axes`). Author supplies an ordered `item_duration_steps` list; engine walks it left-to-right on advance, right-to-left on regression. `sequential` stays two-phase; chain drills if you want item_duration ramping plus phased tempo/density work. |
| `coupled_axes` ordered list replaces `coupling_pattern`; list order is the round-robin advance order | Keep `coupling_pattern` enum and add parallel fields for item_duration | One list expresses both "which axes participate" and "in what order they advance" — no enum explosion when a third axis joined. Default `[tempo, density]` preserves prior behavior. |
| DAG is a forest of topic nodes; drill association is per-node and optional; node completion criteria observe drill milestones at specific thresholds | Every node has a drill / one node per drill / drills are a separate graph | Matches the authoring model: some topics are concept anchors (no drill, manual user toggle to complete), others observe a specific milestone on a drill (e.g. "Drill A at 70 BPM" vs "Drill A at 100 BPM 16th notes" are two distinct nodes both watching the same long-lived drill). Drill keeps growing; nodes are stationary checkpoints. |
| Non-drill DAG nodes complete via manual user toggle; drill-bearing nodes are strictly engine-computed | Manual override allowed on drill nodes too / require every node to have a drill | Honest-user model still applies (user controls the drill config), but drill-node completion is a real engine signal — letting users hand-mark them complete short-circuits the practice loop the tool exists to support. Concept anchors *must* be manual because there's nothing to detect. |

### ML / song practice (Stage 3)

| Decision | Rejected alternative | Why |
|---|---|---|
| CPU-only ML | GPU-accelerated | User constraint. Demucs has CPU-friendly variants; Basic Pitch is lightweight. |
| ML models as subprocesses; optional ONNX-in-Rust later (Stage 3.5) | ONNX-from-day-one | Subprocesses are simpler to wire up. Validate the feature on the easy path; escalate to ONNX-in-Rust only if appetite remains. |
| No cloud features at all | Optional cloud transcription / separation for quality | Explicit user constraint. Fully local. |

---

## Out of scope (don't re-propose)

Some of these are also in `high_level_plan.md`'s out-of-scope list, repeated
here so they sit next to the rationale.

- **Cloud features of any kind.** Hard constraint.
- **Multi-user, accounts, auth.** Single-user personal tool.
- **Live note-by-note visual feedback during play.** Replaced by audio-feedback channel for the human-reaction-time reasons above.
- **Songsterr-style polished engraving.** Functional view only.
- **Karaoke-mode cursor** that waits for the player.
- **Stacked staff + tab.** Tab XOR staff per drill.
- **Authoring drills via in-app GUI editor** (Stage 1). YAML edits by hand; GUI authoring is a possible Stage 1.5+ addition.
- **Multi-step regression drops.** Single step on the last-advanced axis, always.
- **Per-drill custom failure responses.** Action is fixed engine behavior; only the trigger sensitivity is per-drill.
- **Anti-cheat / input validation against gaming the stats.** Honest-user model.

---

## Open questions / not yet decided

If a new agent encounters these and needs to act on them, **ask the user**
— they haven't been settled.

- **Default values for `M` (clean-bar threshold)**, `*_tolerance_pct`, and `tempo_step`. User said "per-drill configuration"; sensible engine-level defaults still need to be picked.
- **Bar-count cap for multi-bar phrase drills.** User said no cap by default; drill author decides.
- **Quiz-me / fretboard-recall mode design.** Sketched in `practice_modes.md`'s Future modes section; full spec pending. Different scoring rule (note correctness, not timing). Requires pitch detection.
- **Tab generation algorithm for Stage 3.** `music21` covers theory primitives, but the actual MIDI-to-fret-position solver is unsolved.
- **GUI authoring tool for drills.** Not in Stage 1.5 plan; might be useful at Stage 1.75 or later.
- **DAG editor UI vs hand-edited JSON.** Both are open. Hand-edited is the Stage 1 path.
- **Stage 3.5 ONNX-in-Rust commitment.** Marked optional; awaits Stage 3 experience.

---

## Reading order for a new agent

1. `decisions.md` (this file) — context + the locked calls.
2. `high_level_plan.md` — feature → language mapping, stages, libraries, architectural anchors.
3. `feature_specs.md` — per-feature Requirements (responsibilities/constraints) and Testing criteria (feature correctness, separate from per-mode tests).
4. `user_workflows.md` — user-facing journeys the system must support (browse the forest, add a drill, run a drill, review history, …). Each journey is also reflected as an implementation hook on the relevant feature in `feature_specs.md`.
5. `practice_modes.md` — drill schema, the five practice modes, per-mode tests, regression mechanics.

Once you've read all five, you should be able to implement any Stage 1
feature without re-asking foundational questions.
