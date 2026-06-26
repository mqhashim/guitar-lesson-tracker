# Dev notes

## Main goals

- app should help user grow as a guitarist
- app should not hinder progress by taking away things the musician should develop
  - for example: App should NOT make moves that might hinder the musicians ear
    training aspect
- Simple, Easy to use, subservient to user.
  - No recommendation algorithms/steering user
  - should lower the friction for organizing lessons, not the friction for
    knowing when to advance or go back
  - should allow users to organize learning direction (which topic to expand next),
    and submit reflections (summary of what they learned).
    - main goal of this is to enable reviewing prerequisites of a topic
- main feature should be the graph, not the practice assistant

## Things that happened

- the drill engine and learning tracker should have been separate app.
- the drill engine (drawing,timing,processing) could be useful for practice,
  but its mainly there for me to practice coding.
- the topic tracker is what I actually want for my own learning journey.

## Drill engine

I want the Drill engine to learn how to tap into recordings and run
light (or heavy) analysis.
This is mainly an exercise in controlling audio through code (reading/outputting)

## Learning Tracker

I want the topic tracker so I can keep track of things I did and long term goals.

- for example: as a daily app it should tell me these are the things I have to
  work on today, and these are the things open for me to explore. I should be
  able to add topics to the graph and link them up (so while exploring topic A,
  I encounter topics B and C, and add them and ref back to A).
- Moreover, I should be able to add more links to stuff (so A -> B -> C, but
  if I encounter another topic D, I could add A-> D later)
- I should be able to say stuff like: take the following, practice daily for the next 3 months,
  and I should be able to track missed days, and the app on launch maybe should remind me.
- maybe a practice session manager, so that it times out the first section (raw practice) after
  some amount of time.
- Should assist in creating, managing, and reviewing recordings.
- should help me measure improvement over time.

## Overlap

There might be some overlap between the two, so there should be a way
to use them in the learning app without getting unneeded things.

Maybe only the metronome would be an overlap? Need to go through these
and iterate. Possibly split this into 2 repos?

## Notes on current AI assisted, bloated, feature crept design

- This
- Practice session scoring should be configurable to only check timing,  
to train the user's ear. In this mode the play head only advances on playing.
