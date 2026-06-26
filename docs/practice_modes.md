# Practice Modes

Concrete drill recipes built on the engine specified in `high_level_plan.md`.
Each entry: what the mode trains, how to configure it (the drill-definition
fields you'd set), and code tests for implementation correctness.

**Test scope clarification**: "Code tests" verify the *engine implementation*,
not the user's playing. Tests use synthetic audio streams (onset, envelope,
articulation cues) and scripted "fake players" to drive the engine through
known scenarios and assert correct state transitions.

---

## Configuration reference

Field-by-field guide to the drill-definition schema. Per-drill fields unless
noted. Engine-level behavior (no field) is called out in the **Regression
strategy** section below.

### Progression

| Field | Values | Notes |
|---|---|---|
| `progression_strategy` | `sequential` \| `coupled` \| `independent` | How tempo, density, and item_duration relate over a session. Each value explained below the table. |
| `progression_axis` | `tempo` \| `density` \| `item_duration` | Used only when `progression_strategy: independent`. The single axis that advances. |
| `coupled_axes` | ordered subset of `[tempo, density, item_duration]` | Used only when `progression_strategy: coupled`. Declares which axes participate and **list order is the round-robin advance order** — first axis in the list ramps first, then wraps. Default `[tempo, density]`. |
| `phase_1_tempo` | BPM (int) | Used only when `progression_strategy: sequential`. The fixed tempo during the density-progression phase. |
| `phase_2_max_tempo` | BPM (int) | Used only when `progression_strategy: sequential`. The tempo cap during the tempo-progression phase. |

**What each `progression_strategy` value does**:

- **`independent`** — One axis advances over the session; the others are fixed. Use for pure speed work (`progression_axis: tempo`), pure internalization (`progression_axis: density`), or pure subdivision work (`progression_axis: item_duration`).
- **`sequential`** — Two phases. Phase 1: density progresses from `start_density` to 3 at `phase_1_tempo`. Phase 2: tempo progresses from `phase_1_tempo` upward at density 3. Internalize first, speed up second. (Does not cover `item_duration`; ramp it via a separate `independent` drill.)
- **`coupled`** — Single auto-ramp rotates through `coupled_axes` in declared order. Each clean ramp advances the next axis; on reaching the list end, the rotation wraps. Balanced; no phase commitment.

### Tempo axis

| Field | Values | Notes |
|---|---|---|
| `start_tempo` | BPM (int) | Starting tempo. Used by `independent` (axis=tempo) and `coupled`. |
| `tempo_step` | BPM (int) | How much tempo advances per ramp. Typically 5–10 BPM. |
| `max_tempo` | BPM (int) \| `null` | Optional cap. Engine stops ramping tempo here. |
| `tempo` | BPM (int) | Fixed tempo when not progressing tempo. Used by `independent` (axis=density). |

### Density axis

| Field | Values | Notes |
|---|---|---|
| `start_density` | `1` (pattern) \| `2` (all subdivisions) \| `3` (pulse only) | Starting click density. Lower number = denser click. |
| `max_density` | `1` \| `2` \| `3` | Optional cap. Engine stops thinning click here. Typically `3`. |
| `density` | `1` \| `2` \| `3` | Fixed density when not progressing density. |
| `subdivision` | `8th` \| `16th` \| `8th_triplet` | The grid the click ticks when at density 2 (all subdivisions). Must be at least as fine as the smallest value in `item_duration_steps` (if used). |

### Item-duration axis

Used by `library_ref` drills. `item_duration` is how long each library item occupies on the grid; making it a ramp axis lets the same library shape be practised at progressively denser note values (quarters → 8ths → 16ths) at fixed tempo and density.

| Field | Values | Notes |
|---|---|---|
| `start_item_duration` | `16th` \| `8th` \| `8th_triplet` \| `quarter` \| `half` \| `whole` \| `bar` | Starting item duration when `item_duration` is a ramping axis (i.e. under `independent` with `progression_axis: item_duration`, or under `coupled` with `item_duration ∈ coupled_axes`). Must be `item_duration_steps[0]`. |
| `item_duration_steps` | ordered list, e.g. `[quarter, 8th, 16th]` | The full ramp path. Engine advances left-to-right; regression steps right-to-left. List order *is* the ramp definition — author can include any values in any order (skips, triplet jumps, both fine). No implicit cap field; the last element is the cap. |

`item_duration` (the fixed-value form in the Pattern section below) is mutually exclusive with `start_item_duration` + `item_duration_steps` — a drill either ramps this axis or fixes it.

### Pattern

A drill supplies its note sequence via **`pattern` XOR `library_ref`** — never both.

| Field | Values | Notes |
|---|---|---|
| `pattern` | List of note records | Inline definition. Each record: `{slot, string, fret, duration, marker}`. `marker` is `accented` \| `normal` \| `muted`. |
| `library_ref` | string (library entry ID) | Cite a reusable entry from the Practice library (e.g. `scales.d_major.position_5`). Library entries are timing-agnostic — they store ordered items where each item is a note `{string, fret, length?}` or a rest `{rest: true, length?}`. `length` (int, default `1`) is a *relative* multiplier in units of `item_duration`; absolute duration on the grid = `item_duration × length × slot_width`. |
| `item_duration` | `16th` \| `8th` \| `8th_triplet` \| `quarter` \| `half` \| `whole` \| `bar` | **Used only with `library_ref`, and only when item_duration is NOT a ramping axis.** Mutually exclusive with `start_item_duration` + `item_duration_steps` (see Item-duration axis above). Sets how long each library item lasts on the grid; engine combines with `subdivision` and per-item `length` to derive slots-per-item, then materialises the same `{slot, string, fret, duration, marker}` shape `pattern` uses. Rests become slot gaps. Markers come from `marker_overlay` if present, else default to `normal`. |
| `marker_overlay` | optional list | **Used only with `library_ref`.** Applies accent / mute markers on top of the resolved sequence at specified item indices. |
| `mode` | `click_with_rhythm` \| `click_against_pulse` | Whether the click sounds the pattern at density 1 (training wheels on) or stays on a straight grid while the user plays the pattern against it. |

### Advancement

| Field | Values | Notes |
|---|---|---|
| `advancement_unit` | `n_bars: N` \| `full_repetition` | The unit the engine counts when checking M clean events. `full_repetition` for cross-neck / spider / motion drills — adjustments happen *between* repetitions, never mid-motion. `n_bars: N` for rhythm / syncopation (set N=1 for per-bar evaluation, larger for longer phrases). |
| `M` | int ≥ 1 | Number of clean units in a row required to trigger a ramp. Per-drill. |

### Scoring

Scoring runs across multiple dimensions. Each tolerance scales to subdivision
width — same percentage at higher tempos = tighter ms tolerance, so drills
get inherently stricter as they speed up.

| Field | Values | Notes |
|---|---|---|
| `onset_tolerance_pct` | float (e.g., `15` for 15%) | Onset (attack) timing tolerance. A 16th @ 120 BPM has a 125 ms slot; 15% ≈ 19 ms. |
| `duration_tolerance_pct` | float; defaults to `onset_tolerance_pct` | How much actual note/chord duration can deviate from the pattern's expected duration. |
| `transition_tolerance_pct` | float; defaults to `onset_tolerance_pct` | Gap-timing tolerance — how much the silence (or its absence) between consecutive notes can deviate from expected. |
| `regression_trigger` | `any_mistake` (default) \| `consecutive: N` \| `per_bar: N` \| `percentage: X` | When the engine fires regression. See **Regression strategy** for details. |

**Scoring dimensions** (what each check measures):

- **Onset timing** — when the attack happens, vs the slot's expected time. Tolerance: `onset_tolerance_pct`.
- **Note/chord duration** — how long the note/chord rings, vs the pattern's `duration` field. Tolerance: `duration_tolerance_pct`.
- **Transition gap timing** — the silence (or its absence) between consecutive notes, vs what the pattern implies. Tolerance: `transition_tolerance_pct`.
- **Articulation match** — binary check, no tolerance field. Expected articulation (connected/legato vs detached) is **derived** from the pattern's `duration` field: if note N's duration extends to N+1's start slot → expect connected; if there's a gap → expect detached. Match or not.
- **Mute discipline** — no extra strums on `muted` slots. Binary; always enforced; no field.

"Attack" today means *attack timing* and is covered by onset timing. Future
scoring may add attack intensity or sharpness as separate dimensions.

### Feedback

| Field | Values | Notes |
|---|---|---|
| `feedback_mode` | `per_pulse_click` \| `bar_end_summary` \| `post_session` | When and how accuracy is signaled back to the player during a session. |

### Session start

When a session begins, the engine prompts the user:

```
warmup? Y/n
```

The answer changes the session's starting parameters. **All sessions count
toward stats** — warmup is about where you *start*, not whether the session
is tracked.

| Path | Starting tempo | Starting density | Ramp behavior |
|---|---|---|---|
| `n` (default) | `previous_best − 1 tempo_step` (or `previous_best` if drill has no tempo ramp strategy) | `previous_best_density` | Normal `tempo_step`. |
| `Y` | drill's `start_tempo` | drill's `start_density` | Expedited until reaching `previous_best`, then normal. |

**Expedited ramp mechanics (Y path)**:

- Engine computes `warmup_tempo_step = ceil((previous_best − start_tempo) / 4)` so `previous_best` is reached in 3–4 clean advancements regardless of the gap size.
- Clean-criteria still required per advancement during warmup. Dirty play doesn't ramp you. The expedite controls *step size*, not *requirement to play clean*.
- When tempo reaches `previous_best`, warmup mode ends; normal `tempo_step` resumes for any further ramping.
- Density progression speed unchanged during warmup; only tempo is expedited.

**Edge cases**:

- **First-ever session** (no `previous_best`): both paths start at the drill's base values; the prompt is suppressed (or shown as inert).
- **`start_tempo ≥ previous_best`** (shouldn't happen with sane drill configs, but possible): warmup mode is a no-op — behaves identically to the `n` path.

### Random generator

Used only by Random-syncopation drills.

| Field | Values | Notes |
|---|---|---|
| `display_mode` | `preview_with_countin` \| `no_preview` \| `lookahead` | How the generated bar is shown. `lookahead` displays the next bar while the current one plays. |
| `generator_constraints.subdivision` | `8th` \| `16th` \| `8th_triplet` | Grid for generated bars. |
| `generator_constraints.target_density` | int or `[min, max]` | Notes per bar. Generator picks count within range. |
| `generator_constraints.accent_distribution` | optional weights | How often accents / mutes appear vs normal notes. |
| `generator_constraints.required_positions` | list of slot indices | Slots that must have a note in every generated bar. |
| `generator_constraints.forbidden_positions` | list of slot indices | Slots that must be silent in every generated bar. |

---

## Regression strategy

### Precondition: the no-play idle-unit gate

Before any clean/dirty evaluation runs, the drill engine checks whether the
player attempted to play during the advancement unit. An advancement unit
with **zero detected player onsets** is **idle** — neither clean nor dirty:

- M-clean counter is **not** incremented.
- Regression does **not** fire.
- Metronome keeps clicking; the engine simply re-evaluates next unit.

**Owner**: the **drill engine** owns this gate. The onset detector stays a
pure DSP module (samples → onset events); the scorer scores any onsets it
sees; the engine decides whether to *apply* the verdict based on onset
count. This keeps "should we even evaluate?" next to the rest of
advancement / regression policy.

### Action when a non-idle unit is dirty

**Where it lives**: in the **engine**, not in the drill definition. There
is no `regression_strategy` or `failure_response` field. The action — what
the engine does when regression fires — is fixed across all drills:

> **Drop back one step on whichever axis last advanced.**

- If the last ramp advanced tempo (`tempo += tempo_step`), regression drops
  tempo by one step.
- If the last ramp thinned density (`density += 1`), regression thickens
  density by one step.
- If nothing has been advanced yet in the session, regression is a no-op
  (you stay at the session's starting values).

**Trigger sensitivity** is configurable per drill via `regression_trigger`:

| Value | Fires when |
|---|---|
| `any_mistake` (default) | A single bad event within the advancement unit. Strictest. |
| `consecutive: N` | N bad events in a row within the advancement unit. |
| `per_bar: N` | ≥N bad events within a single bar. |
| `percentage: X` | Bad-event percentage over the advancement unit exceeds X%. |

A "bad event" = any scoring-dimension failure (onset timing, duration,
transition gap, articulation, or mute discipline).

When triggered, the engine fires regression once and resets the
M-clean-counter to zero. The next M consecutive clean units are required to
re-advance.

**No multi-step drop**: even severe failures only drop one step. By design —
the `advancement_unit` is the engine's unit of evaluation; it doesn't try to
reason about *how badly* you missed within a unit.

**Interaction with progression strategy** (which axis regression drops):

| `progression_strategy` | Axis dropped |
|---|---|
| `independent` (axis=tempo) | Tempo |
| `independent` (axis=density) | Density |
| `sequential` (phase 1, density progressing) | Density |
| `sequential` (phase 2, tempo progressing) | Tempo |
| `coupled` | Whichever axis the most recent ramp advanced |

---

## 1. Speed drill

**What it trains**: Pure tempo progression. Density stays fixed. The go-to
mode for technique work — scales, spiders, picking patterns, cross-string
runs — where the same notes get progressively faster.

**Configuration**:

- `progression_strategy: independent`
- `progression_axis: tempo`
- `start_tempo: <BPM>`
- `tempo_step: <BPM increment per ramp>`
- `max_tempo: <optional cap>`
- `density: fixed` (typically `pulse_only` for scales)
- `pattern: [notes — string / fret / duration / marker]`
- `mode: click_against_pulse` (typical for technique drills)
- `advancement_unit: full_repetition` (for spiders/scales) or `n_bars: N`
- `M: <clean units required to advance>`
- `onset_tolerance_pct: <e.g., 15>`
- `duration_tolerance_pct: <optional; defaults to onset>`
- `transition_tolerance_pct: <optional; defaults to onset>`
- `regression_trigger: any_mistake` (or `consecutive: 2`, etc.)
- `feedback_mode: per_pulse_click | bar_end_summary | post_session`

**Code tests**:

- *Unit* — Drill YAML parses with required fields; missing or invalid fields
  rejected at load.
- *Unit* — `tempo_step` applied correctly on ramp.
- *Unit* — Each tolerance scales correctly: e.g., 15% of slot width at
  16ths @ 120 BPM ≈ 19 ms.
- *Integration* — Feed M consecutive clean synthetic units → engine
  advances tempo by `tempo_step`.
- *Integration* — Feed a dirty unit after a ramp → engine drops back to the
  previous tempo.
- *Integration* — `start_tempo == max_tempo` → engine never advances; ramp
  trigger fires but no-ops.
- *Fake-player E2E* — Scripted "always clean" player runs M × K units →
  engine reports `fastest_clean_tempo = start_tempo + K * tempo_step`.

---

## 1.5. Subdivision-ramp drill

**What it trains**: Same library shape played at progressively denser note
values — e.g. quarters → 8ths → 16ths — at fixed tempo and fixed density.
Internalizes the shape across multiple rhythmic readings without changing
the click feel or pushing BPM. Most useful for scales, arpeggios, and
spider patterns where the shape is mastered but rhythmic placement varies.

**Configuration**:

- `progression_strategy: independent`
- `progression_axis: item_duration`
- `tempo: <fixed BPM>`
- `density: <fixed, typically 3 (pulse only)>`
- `library_ref: <e.g., scales.d_major.position_5>`
- `start_item_duration: quarter`
- `item_duration_steps: [quarter, 8th, 16th]` (any ordered subset of the
  item_duration enum the author wants — skips allowed, triplet jumps
  allowed)
- `subdivision: 16th` (fine enough to host the smallest step in the list)
- `mode: click_with_rhythm` (typical) or `click_against_pulse`
- `advancement_unit: full_repetition` (typical for scale shapes)
- `M`, `onset_tolerance_pct`, `duration_tolerance_pct` (optional),
  `transition_tolerance_pct` (optional), `regression_trigger`, `feedback_mode`

**Code tests**:

- *Unit* — `item_duration_steps: [quarter, 8th, 16th]` resolves to three
  distinct materialised patterns at drill-load (one per step).
- *Unit* — Engine rejects drills where `start_item_duration ≠
  item_duration_steps[0]` at load time.
- *Unit* — Engine rejects drills where `subdivision` is coarser than the
  finest value in `item_duration_steps`.
- *Integration* — Feed M clean reps at quarters → engine advances to 8ths;
  M more clean reps → advances to 16ths; M more → stays at 16ths (list
  end).
- *Integration* — Dirty rep at 16ths drops back to 8ths; dirty rep at
  `item_duration_steps[0]` is a no-op (can't drop below the first step).
- *Fake-player E2E* — Clean traversal through the full step list reaches
  the final item_duration; per-density stats record clean passes at each
  step value.

---

## 2. Internalization drill

**What it trains**: Pure density progression. Tempo stays fixed. For
internalizing a rhythm at a comfortable tempo by thinning the click until
you can hold the pattern against just the pulse.

**Configuration**:

- `progression_strategy: independent`
- `progression_axis: density`
- `tempo: <fixed BPM>`
- `start_density: 1` (pattern)
- `max_density: 3` (pulse only)
- `pattern: [notes with accent/mute markers]`
- `subdivision: 8th | 16th | 8th_triplet`
- `mode: click_with_rhythm`
- `advancement_unit: n_bars: 1` (or larger for longer phrases)
- `M`, `onset_tolerance_pct`, `duration_tolerance_pct` (optional),
  `transition_tolerance_pct` (optional), `regression_trigger`, `feedback_mode`

**Code tests**:

- *Unit* — At density 1, metronome plays only drill notes. At density 2,
  metronome plays every subdivision slot. At density 3, metronome plays
  only pulse.
- *Unit* — Density transition fires on M clean units.
- *Integration* — Clean unit at density 1 → advance to density 2 → clean →
  density 3 → clean → stays at density 3 (max reached).
- *Integration* — Dirty unit at density 3 → drops back to density 2.
- *Integration* — Failure drop never falls below `start_density`.
- *Fake-player E2E* — Clean player passes M units at each density → stats
  record clean passes at all three densities.

---

## 3. Sequential drill

**What it trains**: Two-phase progression. Phase 1: density progression at
fixed low tempo. Phase 2: tempo progression at fixed thinnest density.
Forces deep internalization before any speed work.

**Configuration**:

- `progression_strategy: sequential`
- `phase_1_tempo: <low BPM>`
- `start_density: 1`
- `phase_2_max_tempo: <cap>`
- `tempo_step`
- `pattern`, `subdivision`, `mode`, `advancement_unit`, `M`,
  `onset_tolerance_pct`, `duration_tolerance_pct` (optional),
  `transition_tolerance_pct` (optional), `regression_trigger`, `feedback_mode`

**Code tests**:

- *Unit* — Phase transition fires exactly when density reaches max.
- *Integration* — Density progresses (1 → 2 → 3) at fixed tempo, then phase
  2 begins; subsequent ramps adjust tempo only.
- *Integration* — Failure during phase 1 drops density, not tempo.
- *Integration* — Failure during phase 2 drops tempo, not density.
- *Fake-player E2E* — Full clean traversal reaches `phase_2_max_tempo` at
  density 3; final stats show both phases completed.

---

## 4. Coupled drill

**What it trains**: Single auto-ramp alternates between advancing tempo and
thinning density. Balanced progression that never lets you over-specialize
on one axis.

**Configuration**:

- `progression_strategy: coupled`
- `coupling_pattern: alternating` (default) | `density_priority` |
  `tempo_priority`
- `start_tempo`, `start_density`, `max_tempo`, `tempo_step`
- `pattern`, `subdivision`, `mode`, `advancement_unit`, `M`,
  `onset_tolerance_pct`, `duration_tolerance_pct` (optional),
  `transition_tolerance_pct` (optional), `regression_trigger`, `feedback_mode`

**Code tests**:

- *Unit* — `alternating` coupling: each clean ramp switches axis (tempo →
  density → tempo → density → …).
- *Integration* — Failure drops back on whichever axis last advanced.
- *Fake-player E2E* — Clean player traverses N ramps → tempo and density
  end states reflect `ceil(N/2)` and `floor(N/2)` advances respectively
  (depending on which axis starts the coupling).

---

## 5. Random-syncopation drill

**What it trains**: Each repeat generates a fresh syncopation pattern under
constraints. Trains quick rhythmic adaptability rather than internalizing
any specific bar — the bar itself isn't important, only the response speed
to it.

**Configuration**:

- `progression_strategy: independent` (typically) — only tempo progresses
- `display_mode: preview_with_countin | no_preview | lookahead`
- `generator_constraints:` (see Configuration reference)
- `start_tempo`, `max_tempo`, `tempo_step`
- `density: 1` (typically — each bar is fresh, no internalization possible)
- `mode: click_with_rhythm` (click always sounds the generated pattern)
- `advancement_unit: n_bars: 1` (each bar is a new pattern)
- `M`, `onset_tolerance_pct`, `duration_tolerance_pct` (optional),
  `transition_tolerance_pct` (optional), `regression_trigger`, `feedback_mode`

**Code tests**:

- *Unit* — Generator output respects `required_positions` (every bar has
  notes there).
- *Unit* — Generator output respects `forbidden_positions` (no bar has
  notes there).
- *Unit* — Generator output respects `target_density` (note count within
  range).
- *Unit* — Generator output is parseable by the same path as authored
  drills.
- *Unit* — Contradictory constraints (overlap of required and forbidden
  positions, target_density unsatisfiable given constraints, etc.) → engine
  rejects drill config at load time with a clear error.
- *Integration* — Each bar generated independently; M consecutive clean
  bars → tempo advances.
- *Integration* — Failure on a generated bar drops tempo; the next bar is
  still freshly generated.
- *Fake-player E2E* — Scripted player that hits all positions successfully
  runs N bars → tempo advances correctly. Verifies the engine exposes the
  generated pattern to the player-abstraction in time for each bar.

---

## Cross-cutting test concerns

These belong in their own test suites, not per-mode:

- **Onset detection accuracy** — fed known WAV files with verified onsets,
  detector reports times within tolerance.
- **Envelope tracking accuracy** — for note-duration measurement: WAVs with
  known sustain lengths, envelope tracker reports durations within
  tolerance.
- **Articulation detection** — WAVs with legato vs detached transitions,
  engine correctly classifies each.
- **Tolerance scaling** — property test: each `*_tolerance_ms` is a fixed
  percentage of `slot_width_ms` across tempos and subdivisions.
- **Session-start paths** — four scenarios:
  - `n` path starts at `previous_best − 1 step`.
  - `Y` path runs expedited ramp (3–4 advancements) until reaching
    `previous_best`, then transitions to normal `tempo_step`.
  - First-ever session: prompt suppressed (or inert); starts at drill base.
  - Edge: `start_tempo ≥ previous_best` → `Y` is a no-op.
- **Regression-trigger handling** — for each `regression_trigger` value:
  - `any_mistake`: single bad event in unit → regression fires.
  - `consecutive: N`: regression fires only after N-in-a-row bad events.
  - `per_bar: N`: regression fires only when ≥N bad events in one bar.
  - `percentage: X`: regression fires only when error rate over unit
    exceeds X%.
- **Audio thread safety** (post-Stage-2) — Rust audio module never blocks
  on Python state; ring buffer never underruns under simulated load.
- **Drill file schema** — round-trip: load → serialize → load produces
  identical drill objects. Schema validation rejects malformed inputs.
- **Progression-strategy telemetry** — per-session records capture the
  strategy used; aggregate query can compare gains across strategies for
  the same drill over time.

---

## Future modes — to expand later

Quiz-me / fretboard-recall modes — different shape from the timing-based
drills above. Scoring rule is **note correctness**, not timing accuracy.
Reuse the DAG, audio capture, and stats backend, but bypass the metronome
/ onset-detection / clean-evaluator pipeline.

To spec when ready:

- **Random scale recall** — engine prompts a scale name (e.g., "D major in
  position 5"); user plays it. **Timing still applies** — engine drives a
  click and verifies notes hit on time, not just in the right order.
  Reuses the click + onset evaluator from the timing drills; layers note
  correctness on top.
- **Random note on a string** — engine names a note + string (e.g., "F# on
  the G string"); user plays it at the correct fret. Score = time from
  prompt to correct onset; aggregate = session-mean response time.
- **Random chord at a position** — engine names a chord + fretboard
  position; user plays a voicing. Score = time from prompt to correct
  onset; aggregate = session-mean response time.
- **Random note across the neck** — engine names a note; user plays every
  occurrence across all strings. Drill config should support **constraining
  to a region of the neck** (exact field shape TBD — possibly
  `neck_region: {min_fret, max_fret}` or named regions; deferred to scoping
  time).

Open questions to resolve when scoping:

- How is note correctness detected? (Pitch detection — different DSP from
  the strum/onset detector this engine uses today.)
- For the time-to-prompt modes (string / chord / across-the-neck): how is
  the prompt cadence set? Fixed interval, or paced by player response?
- Do they have a progression model (e.g., shrinking response window over
  time), or just pass/fail per prompt with the session mean as the signal?
- Do they integrate with the DAG (recall failure marks a node as needing
  review)?
- For random-note-across-the-neck: shape of the `neck_region` constraint —
  bare integers, named regions backed by the practice library, or both.
