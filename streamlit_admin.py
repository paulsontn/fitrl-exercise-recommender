import streamlit as st
import os
import sys
import json
import threading
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
MODEL_FILE = ROOT / "trained_agent.pt"

st.set_page_config(page_title="Project Admin", layout="wide")

# Helper: run background process and capture logs
def _start_process(name, args):
    key_proc = f"proc_{name}"
    key_log = f"log_{name}"
    if key_proc in st.session_state and st.session_state[key_proc] is not None:
        return False, f"{name} already running"

    # start subprocess with current interpreter
    try:
        proc = subprocess.Popen([sys.executable] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        return False, f"Failed to start {name}: {e}"

    st.session_state[key_proc] = proc
    st.session_state.setdefault(key_log, "")

    # background thread to read stdout
    def _reader():
        try:
            for line in proc.stdout:
                st.session_state[key_log] += line
        except Exception as e:
            st.session_state[key_log] += f"\n[reader-error] {e}\n"

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    return True, f"Started {name}"


def _stop_process(name):
    key_proc = f"proc_{name}"
    key_log = f"log_{name}"
    proc = st.session_state.get(key_proc)
    if not proc:
        return False, f"{name} not running"
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception as e:
            return False, f"Failed to stop {name}: {e}"
    st.session_state[key_proc] = None
    st.session_state.setdefault(key_log, "")
    st.session_state[key_log] += "\n[process stopped]\n"
    return True, f"Stopped {name}"


# UI
st.title("Admin Dashboard — Project Controls")

cols = st.columns([1, 2])
with cols[0]:
    st.header("Project Status")
    st.markdown(f"**Project root:** `{ROOT}`")
    files = sorted([p.name for p in ROOT.iterdir() if p.is_file()])
    st.write("Files in project root:")
    st.write(files)
    st.write("")
    st.markdown("**Model status**")
    if MODEL_FILE.exists():
        st.success(f"Model file found: `{MODEL_FILE.name}`")
        st.write(f"Size: {MODEL_FILE.stat().st_size} bytes")
    else:
        st.warning("No trained model file found (`trained_agent.pt`).")

    st.markdown("**Data / User history**")
    if DATA_DIR.exists():
        hist_files = sorted([p.name for p in DATA_DIR.glob("*_history.json")])
        st.write(f"Found {len(hist_files)} user history files")
        st.write(hist_files)
    else:
        st.info("No `data/` directory present yet.")

    # Export combined histories
    if st.button("Export all histories (JSON)"):
        combined = {}
        if DATA_DIR.exists():
            for p in DATA_DIR.glob("*_history.json"):
                try:
                    combined[p.stem] = json.load(open(p, "r", encoding="utf-8"))
                except Exception as e:
                    combined[p.stem] = {"error": str(e)}
        st.download_button("Download combined histories JSON", json.dumps(combined, indent=2), file_name="all_histories.json")

with cols[1]:
    st.header("Project Actions")

    # Provide quick wrappers for scripts
    st.subheader("Background processes & logs")

    # Training
    if st.button("Start quick training (10 episodes)"):
        started, msg = _start_process("training", ["main.py", "--num_episodes", "10"]) if (ROOT / "main.py").exists() else (False, "main.py not found")
        st.info(msg)
    if st.button("Stop training"):
        stopped, msg = _stop_process("training")
        st.info(msg)

    # API
    if st.button("Start API server"):
        started, msg = _start_process("api", ["api.py"]) if (ROOT / "api.py").exists() else (False, "api.py not found")
        st.info(msg)
    if st.button("Stop API server"):
        stopped, msg = _stop_process("api")
        st.info(msg)

    # Smoke tests
    if st.button("Run smoke tests: timed recommendations"):
        if (ROOT / "test_timed_recommendations.py").exists():
            started, msg = _start_process("smoke_timed", ["test_timed_recommendations.py"]) 
            st.info(msg)
        else:
            st.error("test_timed_recommendations.py not found")
    if st.button("Run smoke tests: multiple-times"):
        if (ROOT / "test_multiple_times.py").exists():
            started, msg = _start_process("smoke_multi", ["test_multiple_times.py"]) 
            st.info(msg)
        else:
            st.error("test_multiple_times.py not found")

    st.write("")
    st.subheader("Live logs")
    logs_tabs = st.tabs(["training", "api", "smoke_timed", "smoke_multi"])
    names = ["training", "api", "smoke_timed", "smoke_multi"]
    for t, name in zip(logs_tabs, names):
        with t:
            key_log = f"log_{name}"
            log_text = st.session_state.get(key_log, "")
            st.text_area(f"Log: {name}", value=log_text, height=300)


st.markdown("---")

# Lower area: exercises and users quick view
st.header("Project Data")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Exercises")
    try:
        import exercise_database as exdb
        exercises = getattr(exdb, "DEFAULT_EXERCISES", None)
        if exercises is None:
            # attempt to inspect names
            exercises = []
            if hasattr(exdb, "default_exercises"):
                exercises = exdb.default_exercises
        if not exercises:
            st.info("No exercises found in `exercise_database.py` exports. Trying to import names.")
            # list attributes
            names = [n for n in dir(exdb) if not n.startswith("_")]
            st.write(names)
        else:
            for e in exercises[:50]:
                try:
                    st.markdown(f"**{getattr(e, 'name', str(e))}** — {getattr(e, 'duration_minutes', '?')} min — {getattr(e, 'calories_burned', '?')} cals")
                except Exception:
                    st.write(str(e))
    except Exception as err:
        st.error(f"Failed to import `exercise_database`: {err}")

with col2:
    st.subheader("Registered Users (histories)")
    if DATA_DIR.exists():
        rows = []
        for p in sorted(DATA_DIR.glob("*_history.json")):
            try:
                payload = json.load(open(p, "r", encoding="utf-8"))
                # try to get basic fields
                uid = p.stem.replace("_history", "")
                last = payload[-1] if isinstance(payload, list) and payload else payload
                rows.append((uid, json.dumps(last)[:200]))
            except Exception as e:
                rows.append((p.name, f"error: {e}"))
        st.table(rows)
    else:
        st.info("No `data/` directory present")

st.caption("Use the buttons above to run training, start the API, run smoke tests, and export histories. Logs stream into the Live logs panels.")
