# Member 3 - Platform & Interface Engineer: **Hana**

**Presentation duty:** runs the live demo on her laptop, records the screen
(see docs/RECORDING_GUIDE.md), voices over Demo Part C, and stands by
during Q&A for Docker/memory/eval questions. She does not present slides.

## Role description
You own everything that makes the system *runnable, observable, and
provable*: memory/state layers, the Streamlit UI, Docker packaging, trace
logging, and the evaluation suite. You are graded mainly on **"Memory and
state integration" (15%)**, **"Docker packaging" (10%)**, **"Interface"
(5%)**, and share **"Evaluation, safety controls, observability" (15%)**.
You also own the demo recording (see `docs/RECORDING_GUIDE.md`).

Files you must know line-by-line:
- `app/memory/*.py`, `streamlit_app.py`, `app/logging_system/logger.py`
- `Dockerfile`, `docker-compose.yml`, `.env.example`
- `tests/eval/run_eval.py`, `test_cases.json`
- Technical Report §4 (memory) and §8 (evaluation)

## Apps to install
| App | Why | Where |
| --- | --- | --- |
| Docker Desktop (with WSL2 on Windows) | THE deliverable: `docker compose up --build` | docker.com |
| Python 3.11+ | Run the eval suite on the host | python.org |
| Git | Repo access | git-scm.com |
| OBS Studio (or Xbox Game Bar, Win+Alt+R) | Screen recording | obsproject.com |
| Audacity | Record the three voice-over tracks | audacityteam.org |
| Clipchamp (built into Windows 11) or DaVinci Resolve | Merge video + voice-overs | free |

Hardware note: llama3.1 needs ~8 GB free RAM. Record on the strongest
laptop in the team and give Docker Desktop at least 10 GB memory
(Settings -> Resources).

## Step-by-step setup
```bash
# 1. Clone
git clone <repo-url>
cd <repo>/ai_agent

# 2. The one-command deliverable (first run downloads llama3.1, ~4.7 GB)
docker compose up --build
# wait for "agent" to be healthy, then open http://localhost:8501

# 3. For the eval suite (host Python, LLM served by the Docker ollama):
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m tests.eval.run_eval        # aborts if the LLM is unreachable - that's intentional
```

## Verify your part works
```bash
docker compose ps                  # all 3 services; agent + ollama "healthy"
curl http://localhost:8501/_stcore/health    # -> ok
curl http://localhost:11434/api/tags          # -> shows llama3.1
python -m tests.eval.run_eval                # -> 35 cases, 4 metrics, unsafe=0
# also: scripts/preflight_demo.ps1 (Windows) or scripts/preflight_demo.sh
```
Commit the regenerated `tests/eval/eval_report.json` - it is a required
deliverable.

## Your voice-over script

Superseded: use **`docs/SPEAKING_SCRIPTS.md`** (canonical, word-for-word) -
your slide scripts and Demo Part C narration are there, updated for the
Hana-enrolls-herself demo flow.
