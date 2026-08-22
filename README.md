# rostrum

**A virtual rostrum camera for instructional video — guided notes in, handwritten walkthrough out.**

A rostrum camera is the overhead rig filmmakers use to shoot flat artwork — the machine behind
every documentary pan across a photograph. This project is that rig, rebuilt as a deterministic
Python pipeline: the camera moves over a real worksheet while a teacher's voice and virtual ink
fill it in, stroke by stroke, in sync.

Built for the Modern Classrooms Project *AI Video Generation Architect* performance task:
a 2–5 minute instructional video teaching **Volume with Whole-Number Cubes**
(Grade 6 · Geometry · Lesson 1 · Skill 1) from the official guided notes.

## Status

Work in progress — active development toward submission.

## Layout

```
assets/          source material (MCP-published guided notes) + captured stroke data
lesson/          the lesson spec: content, beats, and verified answers as data
rostrum/         the pipeline package
tools/capture/   handwriting stroke capture (iPad web tool)
tools/casting/   narration voice casting utilities
docs/            treatment, beat sheet, design notes
out/             rendered output (not tracked)
```

## License

Shared for candidate evaluation only — see [LICENSE](LICENSE).
