# Recording Guide - Run Once on One Laptop, Voice-Over Later

Yes, this works and is safer than a live demo: **one person drives and
records the screen silently; each member records their narration afterwards
over their own segment.** The word-for-word narration scripts AND the step-by-step demo with verbatim
expected answers are in `docs/SPEAKING_SCRIPTS.md` (canonical).

## Step 1 - Prepare the laptop (Member 3, day before)

1. Use the strongest laptop (8+ GB free RAM for llama3.1; give Docker
   Desktop 10 GB in Settings -> Resources).
2. `docker compose up --build` once, wait until healthy, open
   http://localhost:8501, send one message to warm the model. Leave the
   containers up (`docker compose up` restarts in seconds next time).
3. Run the check: `scripts\preflight_demo.ps1` (or `./scripts/preflight_demo.sh`).
   To RE-record the enrollment scene, reset the data first:
   `docker compose down -v && docker compose up` (reseeds; Hana Tfaily starts
   un-enrolled with balance 4000.00).
4. Turn on Do Not Disturb / Focus Assist. Close email, chat, and anything
   with notifications. Hide bookmarks bar. Set display scaling ~125% so the
   chat text is readable at 1080p.
5. Regenerate the eval report so it's fresh: `python -m tests.eval.run_eval`.

## Step 2 - Record the screen ONCE, silently (one person drives)

Recorder: OBS Studio (display capture, 1920x1080, 30 fps, mp4) or
Xbox Game Bar (Win+Alt+R). **Mute the microphone** - voice comes later.

Shot list (target ~7 minutes raw; pauses are fine, they get trimmed):

| Scene | What to show | Type (from PRESENTATION_PLAN §3) | ~Time |
| --- | --- | --- | --- |
| 0 | Terminal: `docker compose up`, then `docker compose ps` showing healthy; browser to localhost:8501 | - | 40s |
| A1 | Sidebar: Name "Maryline Karam", Role "Student" | CE410 course question | 30s |
| A2 | Switch Role to "Registrar Staff" | Nour Hamad eligibility for CE410 | 30s |
| B1 | Sidebar: Name "Hana Tfaily", Role "Student"; zoom on the workflow-state panel after the reply | `I'd like to enroll in CE410 for Spring 2026.` | 40s |
| B2 | Keep the working-memory panel visible | `yes` (fee 1800.00 deducted, new balance 2200.00) | 30s |
| B3 | - | `Enroll me in CE410 again.` then `no` | 35s |
| B4 | - | flight to Paris (exact fallback, zero tools) | 25s |
| B5 | - | `talk to a human` (HANDOFF ticket) | 25s |
| C1 | Point mouse at the working-memory panel | `What is my GPA summary?` (as Hana - no name typed) | 30s |
| C2 | - | `And my transcript summary?` | 25s |
| C3 | Terminal: `python -m tests.eval.run_eval` scrolling, ending on the 4 metrics (or show the committed eval_report.json metrics) | - | 60s |

Driving tips: move the mouse slowly and deliberately; after each agent
reply, hold still 3 seconds (gives the editor room to cut); if a scene goes
wrong, just pause 5 seconds and redo it - trim later. Local LLM replies can
take 10-30 s; don't fill the silence, it will be cut or covered by narration.

## Step 3 - Each member records their voice-over

1. Each member opens their script (`docs/team/MEMBER<n>_*.md`, last section)
   and the trimmed video segment for their part (A -> Member 1, B -> Member 2,
   C -> Member 3).
2. Record in Audacity while watching the muted video: quiet room, phone
   mic 10-15 cm away is fine, one continuous take per part, re-read a
   sentence immediately if you stumble (edit out the flub later).
3. Export each track as WAV/MP3: `voiceover_A.wav`, `voiceover_B.wav`,
   `voiceover_C.wav`.

## Step 4 - Merge (Member 3, in Clipchamp or DaVinci Resolve)

1. Import the screen recording; cut dead waiting time (keep ~1-2 s of each
   "thinking" moment so it looks real - don't hide model latency entirely).
2. Drop the three voice tracks under their scenes; nudge until each
   "[screen: ...]" cue in the script lines up with the matching moment.
3. Optional: 2-second title card (project name + the three members + roles)
   and end card (GitHub repo URL + metrics table).
4. Export: 1080p, mp4. Target final length **6-8 minutes**.
5. Watch it start-to-finish once, all three members together, before submitting.

## Fallback if asked to demo live anyway
The containers are already built - `docker compose up` starts in seconds.
Drive the same shot list live; the video remains your backup.
