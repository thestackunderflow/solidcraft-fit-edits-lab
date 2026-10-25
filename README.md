# SolidCraft fit-edits lab: does a 0.2 mm fit survive three edits?

The lab behind "SolidCraft + Claude: The 0.2 mm Fit Held, a Hole Stopped 3 mm Short" (SolidCraft for Beginners #8, The
Stack Underflow). Claude Code designs a peg block and a plate that fit over it with a 0.2 mm gap on each side of every
peg, then edits the design three times, each edit in a brand-new chat. After every edit the lab exports the saved design,
cuts it open and measures the gap. Everything runs in Docker on SolidCraft 0.22.0. Tested 25 Oct 2026.

## What the video tested
A clearance gap is the small space between a peg and its hole so the two parts slide together after printing. The
question: when you come back later and change the design, does the gap stay 0.2 mm?

- The first chat builds it: a peg block 80 x 30 x 4 mm with two 5 mm pegs, and a plate 80 x 30 x 5 mm on top, with a
  hole 0.4 mm bigger than each peg.
- Three edits, each in a new chat that only gets the saved design: (1) pegs 5 to 6 mm, (2) add a third peg in the
  middle, (3) plate 5 to 8 mm thick. The edit prompts never mention the gap.
- Three ways of telling Claude about the gap, three runs each (9 runs, 36 sessions):
  - `once`: the gap is only in the first message;
  - `named`: the first message asks for a named size (a parameter) called `fit_gap` and holes worked out from it;
  - `claudemd`: the same, plus a two-line `CLAUDE.md` note in every chat's folder.
- Each chat starts sealed: no session history, auto memory off, and every `CLAUDE.md` outside the chat's own folder left
  out. `prerun-files.txt` (what was on disk before the chat) and `instructions-loaded.jsonl` (what Claude Code says it
  loaded) in each edit folder show that. Host paths in those two logs are replaced with `C:\Users\you\lab`.

The exact prompts are in `claude-run/run.sh`.

## What it found
- **The gap held in 27 of 27 edits**, in all three ways of telling it (9 of 9 each). Measured 0.2008 to 0.2032 mm each
  side; the first build measured 0.2039. The pass rule is 0.2 mm plus or minus 0.03, on the worst side of every hole.
  (`out/runs/SCORES.json`)
- **What broke was the third hole.** We only asked for a third peg; Claude added the matching hole in all 9 runs. In 5 of
  9 runs (claudemd-1, -2, -3, named-2, once-3) it was its own cut, 5 mm deep, the plate's thickness at the time. In the
  other 4 the new circle went into the sketch the first two holes came from. (`out/runs/*/edit-2/transcript.jsonl`)
- When the plate went to 8 mm, 3 of those 5 runs deepened that cut and 2 did not (claudemd-1 and claudemd-3): the middle
  hole stops 3 mm short, under 3 mm of plastic. SolidCraft rebuilt with no error. The scorer marks those edits
  "holes not through". (`out/runs/claudemd-1/edit-3/score.json`, `video/frames/fit-edit3-blind.png`)
- Both short holes came from the `CLAUDE.md` runs. Three runs per way are too few to blame the note; the note was about
  the gap, not the depth.
- Claude's own answer after edit 3 in claudemd-1: "every hole keeps its 0.2 mm gap per side". True, but it did not check
  that the holes still go through.
- The measurement itself was checked first, with no AI (`out/probe/`): a reference plate measures 0.20 mm each side and
  passes; a "lost gap" plate (hole = peg) and a plate with one peg moved 0.1 mm both fail.
- Cost: 36 Claude Code sessions (claude-sonnet-5-5, Claude Code 2.1.310), $3.38 at API prices, from each edit's
  `meta.json`.

Nothing was printed. Every size is measured in the saved design. A printed 0.2 mm hole usually comes out a little tight:
print a test peg before you trust 0.2 mm on your printer.

The lesson: write down what must stay true (the gap, and that holes go through), and measure after every edit. "No
errors" means it rebuilt, not that it is still what you designed.

## Run the lab
You need Docker. Nothing is installed on your computer.
```
docker build -t solidcraft-fit-edits-lab:0.22.0 .
docker run --rm -v "$PWD:/work" -w /work solidcraft-fit-edits-lab:0.22.0 python3 -m pytest -q tests/
docker run --rm -v "$PWD:/work" -v "$PWD/out/probe:/lab/out" -w /work solidcraft-fit-edits-lab:0.22.0 python3 probe/probe.py
bash claude-run/score_all.sh
```
The build downloads the SolidCraft 0.22.0 Linux release and checks it against the release's SHA256SUMS.txt. The tests
run offline. The probe needs no AI and no money. `score_all.sh` re-scores the saved designs already in `out/runs/` (it
skips a run whose `edit-0/score.json` exists, so delete that file to redo a run).

To run Claude yourself: `bash claude-run/run.sh once|named|claudemd RUN_ID` (needs Claude Code and an API key; each
session is capped at $0.60 and a shared budget file is checked first; see the top of `run.sh`).

## Layout
- `fit/gap.py`: the gap measurement (round loops in a cross-section, circle fits, hole and peg pairs, worst side) and
  the pass rule.
- `probe/probe.py`: the no-AI check of the measurement (reference, lost gap, shifted peg). Results in `out/probe/`.
- `claude-run/`: `run.sh` (one run = 4 sealed sessions), `score.py` and `score_all.sh` (re-open each saved design, export
  it, measure), `budget.py` (the spending cap), `prerun.py` (the file search before each session).
- `proxy/mcp_log_proxy.py`: sits between Claude Code and SolidCraft and logs every request and reply to
  `transcript.jsonl`.
- `out/runs/ARM-N/edit-E/`: per session the prompt, Claude's output, the MCP log, the saved design (`work/`), the
  exported STLs (`score/`) and the score. `out/runs/SCORES.json`: the table for all 9 runs.
- `out/*.log`: the red (failing first) and green test logs, and each run's console log.
- `tests/`: the tests for the measurement, the STL reader and the budget.
- `video/`: the section drawings and cards used in the video, made from the scored STLs (`draw_fit.py`, `make_cards.sh`).

## Licence
Apache-2.0 (`LICENSE`). Not affiliated with SolidCraft or Anthropic. Narration of the video: AI-generated voice.
