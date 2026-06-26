# User Workflows

The journeys the user actually performs with the tool. Each section
describes **what the user sees and does**, not how the system implements
it. Implementation owners are listed at the end of each journey and
expanded in `feature_specs.md` as Requirements bullets keyed
"Implements workflow: …".

This file is normative for the UX target — if a feature can't support
these flows it isn't done.

---

## 1. Browse the forest

**What the user wants**: see the whole topic landscape at a glance —
what's done, what's open, what's still locked behind work.

**What they do**:

1. Open the app (CLI, TUI, or GUI) and land on the forest view.
2. See multiple disconnected DAGs side-by-side or in a navigable list.
   Each node shows:
   - Completed nodes — visually distinct (checked / greyed).
   - Unlocked-but-untouched nodes — highlighted as available next steps.
   - Locked nodes — dimmed, with the unlock requirements readable on
     hover / select.
3. Navigate freely — no forced order beyond unlock edges.

**Implementation owners**: DAG topic tracker (data + completion state) +
TUI app / GUI app / CLI (rendering).

---

## 2. Focus a lesson

**What the user wants**: pick a topic, see what it is, see what it unlocks,
and either start its drill or mark it complete by hand.

**What they do**:

1. Select a node from the forest view.
2. See the node detail:
   - Title, description.
   - Associated drill (if any) with a "Start drill" action.
   - Downstream nodes this topic would unlock on completion.
   - For non-drill nodes only: a "Mark complete" toggle.
   - For drill-bearing nodes: completion criterion shown read-only (e.g.
     "Drill A cleared at ≥100 BPM, ≥density 3, ≥16ths").
3. Either start the drill or mark complete (non-drill nodes only).

**Implementation owners**: DAG topic tracker (node metadata + manual
toggle path) + TUI app / GUI app / CLI (detail view).

---

## 3. Add a drill

**What the user wants**: write a YAML file describing the drill and have
the system pick it up. They don't want to think about ingestion, indexing,
or registration steps.

**What they do**:

1. Author a drill YAML by hand — inline `pattern` or `library_ref` +
   `item_duration`, progression strategy, tolerances, feedback mode, etc.
   (Schema in `practice_modes.md`.)
2. Drop the file in the drills directory.
3. On next session list (CLI / TUI / GUI), the drill appears. No
   ingestion command, no registry edit.
4. If the YAML is malformed or cites an unknown `library_ref`, the system
   tells them which file failed and why — in plain language, with file
   path and field.

**Implementation owners**: Drill engine (auto-discovery + load validation
+ error surfacing) + CLI (the listing surface that proves it worked).
Authoring is out of band — there is no in-app drill editor in Stage 1.

---

## 4. Run a drill

**What the user wants**: pick a drill, answer the warmup prompt, play.
Tempo, density, advancement, regression — the engine handles all of it.

**What they do**:

1. Pick a drill — by ID from a node detail view, or directly from a drill
   listing.
2. Engine prompts `warmup? Y/n` (suppressed on first-ever session of that
   drill). Per `practice_modes.md` Session start.
3. Session loop runs:
   - Metronome clicks at the engine's current tempo / density.
   - Renderer shows the pattern with the clock-driven playhead.
   - Player plays. If they don't, the engine **keeps clicking and
     re-evaluating** — no advance, no regress while idle.
   - When they do play, the scorer evaluates, the engine applies the
     verdict, ramps or regresses per the drill's strategy.
   - Feedback fires per drill's `feedback_mode` (per-pulse-click pitch,
     bar-end summary, or post-session only).
4. Session ends on user exit. Engine writes the session record + emits
   any milestone events; the DAG topic tracker observer updates affected
   nodes.

**Implementation owners**: Drill engine (warmup prompt, session loop,
idle-unit gate, ramp/regression, milestone emission) + Metronome +
Renderer (tab or staff) + Audio feedback channel + Per-drill progress
tracking + CLI / TUI / GUI (launch entrypoint).

---

## 5. Review past sessions

**What the user wants**: see how a drill has been going. Where they
plateau, which strategy is paying off, which density they get stuck on.

**What they do**:

1. From a drill listing or node detail, open the drill's history.
2. See:
   - Tempo curve over time per density (where they peak, where they stall).
   - Fastest clean tempo per density level.
   - Per-session: progression strategy used, warmup or not, tempo
     reached, density reached.
   - Progression-strategy telemetry — which strategy yielded faster gains
     over time on this drill.
3. Use the insight to author a new drill or pick a different progression
   strategy next session. (No in-app suggestion engine in Stage 1 —
   insight stays human.)

**Implementation owners**: Per-drill progress tracking (data + derived
stats) + CLI / TUI / GUI (history surface).

---

## Out of scope for Stage 1 workflows

These are documented as user journeys we deliberately *don't* support
yet, so a new agent knows not to invent them:

- **In-app drill authoring** (drag-and-drop pattern editor, fretboard
  picker). YAML by hand only. `decisions.md` notes a possible Stage 1.5+
  addition.
- **In-app forest authoring beyond JSON edits** (visual DAG editor with
  click-and-drag unlocks). DAG editor UI vs hand-edited JSON is an open
  question in `decisions.md`.
- **Cloud sync of progress / sessions / forests**. Hard constraint per
  `decisions.md`.
- **Multi-user accounts / sharing forests**. Single-user personal tool.
- **Live note-by-note visual mistake highlighting during play**. Replaced
  by the audio-feedback channel per `decisions.md` (human-reaction-time
  floor makes live visual feedback functionally useless).
- **Karaoke-mode session loop that waits for the player**. The playhead
  is clock-driven and never waits.
