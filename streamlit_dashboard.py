"""
Streamlit Dashboard for RL Exercise Recommendation System

Run with:
    streamlit run streamlit_dashboard.py
"""

import json
import sys
import threading
import subprocess
import importlib
import importlib.util
import platform
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from exercise_analytics_v2 import ExerciseAnalytics
from recommendation_system import RecommendationSystem
from user_profile import FitnessLevel, UserGoal, UserProfile

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
MODEL_FILE = ROOT_DIR / "trained_agent.pt"

COMMON_INJURIES = [
    "knee_pain",
    "ankle_pain",
    "shoulder_pain",
    "wrist_pain",
    "chest_pain",
    "back_pain",
    "lower_back_pain",
    "elbow_pain",
    "neck_pain",
]

COMMON_EQUIPMENT = [
    "dumbbells",
    "barbell",
    "bench",
    "pull_up_bar",
    "dip_bars",
    "leg_press_machine",
    "bicycle",
    "kettlebell",
    "mat",
    "resistance_bands",
]


@st.cache_resource
def get_system() -> RecommendationSystem:
    """Instantiate and cache the recommendation system."""
    return RecommendationSystem(agent_path=str(MODEL_FILE), data_dir=str(DATA_DIR))


def _render_recommendation_cards(recommender, recs: list, prefix: str):
    """Render expandable exercise cards with safety alerts, feedback sliders, and completion tracking."""
    for i, rec in enumerate(recs):
        slider_key = f"{prefix}_{rec['exercise_id']}_{i}_score"
        fb_btn_key = f"{prefix}_fb_{rec['exercise_id']}_{i}"
        complete_key = f"{prefix}_complete_{rec['exercise_id']}_{i}"

        safety = rec.get("safety_info") or recommender.get_safety_info(rec["exercise_id"])
        badge = "⚠️" if safety.get("unsafe") else "✅"

        with st.expander(
            f"{badge} #{rec.get('rank', i + 1)} {rec['exercise_name']} • {rec['duration_minutes']} min • Intensity {rec['intensity_level']}/10",
            expanded=(i == 0)
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Duration", f"{rec['duration_minutes']} min")
            c2.metric("Intensity", f"{rec['intensity_level']}/10")
            c3.metric("Calories/min", f"{rec['calories_burned']}")
            total_cals = rec.get("total_calories", rec["duration_minutes"] * rec["calories_burned"])
            c4.metric("Est. Total", f"{total_cals:.0f} kcal")

            c5, c6, c7 = st.columns(3)
            c5.write(f"**Sets:** {rec['sets']}")
            c6.write(f"**Reps/Duration:** {rec['reps']}")
            eq_list = rec.get("equipment_required") or []
            c7.write(f"**Equipment:** {', '.join(eq_list) if eq_list else 'Bodyweight only'}")

            st.write(f"**Description:** {rec['description']}")
            st.write(f"**Why Recommended:** {rec['rationale']}")

            if safety.get("unsafe"):
                st.warning(f"Safety Alert: {safety.get('notes')} (Recommended safe duration: {safety.get('safe_duration')} min)")
            else:
                st.info(f"Guidance ({safety.get('best_exercise_type', 'general').title()}): {safety.get('notes')} • Recommended Intensity: {safety.get('recommended_intensity')}/10")

            default_score = float(recommender.user_feedback.get(rec["exercise_id"], 7.5))
            score = st.slider(
                f"Rate satisfaction for {rec['exercise_name']}",
                0.0,
                10.0,
                default_score,
                step=0.5,
                key=slider_key
            )

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("💬 Save Rating", key=fb_btn_key, use_container_width=True):
                    recommender.provide_feedback(rec["exercise_id"], float(score))
                    st.success(f"Saved {score}/10 rating for {rec['exercise_name']}")

            with btn_col2:
                if st.button("✅ Mark Completed", key=complete_key, use_container_width=True):
                    try:
                        entry = recommender.record_completion(rec["exercise_id"], satisfaction_score=float(score))
                        st.success(f"Completed! Reward: {entry.get('reward')} | Satisfaction: {entry.get('satisfaction')}/10")
                    except Exception as e:
                        st.error(f"Failed to record completion: {e}")


def user_registration_ui(sys_obj: RecommendationSystem):
    st.header("👤 Register or Update User Profile")
    st.markdown(
        "Create a personalized profile so the RL recommender can tailor workouts to your fitness level, "
        "goals, injuries, available equipment, and daily recovery status."
    )

    with st.form("register_form"):
        col1, col2 = st.columns(2)

        with col1:
            user_id = st.text_input("User ID", value=f"user_{len(sys_obj.user_manager.profiles) + 1}")
            age = st.number_input("Age", min_value=13, max_value=100, value=30)
            fitness_level = st.selectbox("Fitness Level", [f.name for f in FitnessLevel])

        with col2:
            goals_mult = st.multiselect(
                "Fitness Goals",
                [g.value for g in UserGoal],
                default=[UserGoal.GENERAL_FITNESS.value]
            )
            available_time = st.number_input("Available Time (minutes)", min_value=5, max_value=240, value=45)

        st.markdown("---")
        st.subheader("🛠️ Equipment, Injuries & Preferences")

        eq_col, inj_col = st.columns(2)
        with eq_col:
            selected_eq = st.multiselect(
                "Select Available Equipment",
                COMMON_EQUIPMENT,
                help="Leave empty if you only do bodyweight exercises."
            )
            extra_eq = st.text_input(
                "Other Equipment (comma-separated, optional)",
                placeholder="e.g. jump_rope, kettlebell"
            )

        with inj_col:
            selected_injuries = st.multiselect(
                "Injuries or Physical Constraints",
                COMMON_INJURIES,
                help="Exercises contraindicated for these injuries will be automatically filtered out."
            )
            extra_injuries = st.text_input(
                "Other Constraints (comma-separated, optional)",
                placeholder="e.g. hip_pain"
            )

        all_ex_names = [ex.name for ex in sys_obj.exercise_db.get_all_exercises()]
        preferred_selected = st.multiselect(
            "Preferred Exercises (optional)",
            all_ex_names,
            help="Select exercises you enjoy to prioritize them in your recommendations."
        )

        st.markdown("---")
        st.subheader("🩺 Daily Recovery & Biometrics (Optional)")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            fatigue = st.slider("Fatigue Level (0 = fully rested, 10 = exhausted)", 0.0, 10.0, 2.0, step=0.5)
            soreness = st.slider("Muscle Soreness (0 = none, 10 = very sore)", 0.0, 10.0, 1.0, step=0.5)
        with b_col2:
            sleep_hours = st.number_input("Sleep Last Night (hours)", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
            resting_hr = st.number_input("Resting Heart Rate (bpm)", min_value=35, max_value=200, value=65)

        submitted = st.form_submit_button("Save User Profile", use_container_width=True)
        if submitted:
            clean_uid = user_id.strip()
            if not clean_uid:
                st.error("Please enter a valid User ID.")
                return

            try:
                fitness_enum = FitnessLevel[fitness_level]
            except Exception:
                fitness_enum = FitnessLevel.BEGINNER

            goals = [UserGoal(g) for g in goals_mult] if goals_mult else [UserGoal.GENERAL_FITNESS]
            equipment_list = list(dict.fromkeys(
                selected_eq + [e.strip().lower() for e in extra_eq.split(",") if e.strip()]
            ))
            injuries_list = list(dict.fromkeys(
                selected_injuries + [i.strip().lower() for i in extra_injuries.split(",") if i.strip()]
            ))

            profile = UserProfile(
                user_id=clean_uid,
                age=int(age),
                fitness_level=fitness_enum,
                goals=goals,
                available_time=int(available_time),
                injuries=injuries_list,
                equipment_access=equipment_list,
                preferred_exercises=preferred_selected,
                fatigue=float(fatigue),
                soreness=float(soreness),
                sleep_hours=float(sleep_hours),
                resting_heart_rate=int(resting_hr)
            )
            recommender = sys_obj.register_user(profile)

            st.success(f"✅ Profile saved for **{clean_uid}**!")
            st.info(
                f"**Equipment:** {', '.join(profile.equipment_access) if profile.equipment_access else 'Bodyweight only'} | "
                f"**Injuries:** {', '.join(profile.injuries) if profile.injuries else 'None'} | "
                f"**Suitable Exercises:** {len(recommender.suitable_exercises)}"
            )


def recommendations_ui(sys_obj: RecommendationSystem):
    st.header("🎯 Personalized Exercise Recommendations")
    profiles = list(sys_obj.user_manager.profiles.keys())
    if not profiles:
        st.info("No users registered yet. Switch to **Register User** in the sidebar to create your first profile.")
        return

    user_id = st.selectbox("Select User", profiles)
    recommender = sys_obj.get_recommender(user_id)
    profile = recommender.user_profile

    st.subheader("📋 Active Profile Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Age", f"{profile.age} yrs")
    col2.metric("Fitness Level", profile.fitness_level.name)
    col3.metric("Available Time", f"{profile.available_time} min")
    col4.metric("Matching Exercises", len(recommender.suitable_exercises))

    c1, c2 = st.columns(2)
    with c1:
        eq_text = ", ".join(profile.equipment_access) if profile.equipment_access else "Bodyweight only"
        st.write(f"**🛠️ Equipment:** {eq_text}")
    with c2:
        inj_text = ", ".join(profile.injuries) if profile.injuries else "None reported"
        st.write(f"**🩹 Constraints:** {inj_text}")

    st.markdown("---")

    mode = st.radio(
        "Recommendation Mode",
        ["Fit to Available Time", "Top N Recommendations"],
        horizontal=True
    )

    state_key = f"active_recs_{user_id}"

    if mode == "Fit to Available Time":
        c_time, c_exp = st.columns([2, 1])
        with c_time:
            target_minutes = st.number_input(
                "Target Workout Duration (minutes)",
                min_value=5,
                max_value=240,
                value=int(profile.available_time),
                step=5
            )
        with c_exp:
            st.write("")
            st.write("")
            exploration = st.checkbox("Include exploration variety", key="timed_exp")

        if st.button("🚀 Generate Timed Workout", type="primary"):
            try:
                recs = recommender.get_recommendations(
                    available_time_minutes=int(target_minutes),
                    use_exploration=exploration
                )
                st.session_state[state_key] = ("timed", recs)
            except Exception as e:
                st.error(f"Error generating timed workout: {e}")

    else:
        max_unique = max(1, len(recommender.suitable_exercises))
        c_num, c_exp = st.columns([2, 1])
        with c_num:
            num_recs = st.slider(
                "Number of Recommendations",
                min_value=1,
                max_value=max(max_unique, 15),
                value=min(5, max_unique)
            )
        with c_exp:
            st.write("")
            st.write("")
            exploration = st.checkbox("Include exploration variety", key="topn_exp")

        if st.button("🚀 Get Recommendations", type="primary"):
            try:
                recs = recommender.get_recommendations(
                    num_recommendations=num_recs,
                    use_exploration=exploration
                )
                st.session_state[state_key] = ("topn", recs)
            except Exception as e:
                st.error(f"Error getting recommendations: {e}")

    # Persist displayed recommendations across Streamlit reruns so sliders & completion buttons work smoothly
    saved = st.session_state.get(state_key)
    if saved:
        rec_mode, recs = saved
        if not recs:
            st.warning("No matching exercises found for your current profile constraints.")
            return

        total_duration = sum(r["duration_minutes"] for r in recs)
        total_calories = sum(r.get("total_calories", 0) for r in recs)
        st.success(f"✅ Ready: **{len(recs)} exercises** • **{total_duration} min** • **~{total_calories:.0f} kcal**")

        display_cols = [
            "rank", "exercise_name", "duration_minutes",
            "intensity_level", "sets", "reps", "total_calories", "rationale"
        ]
        df = pd.DataFrame(recs)
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True, hide_index=True)

        # Export buttons with flattened safety metadata
        export_recs = []
        for rec in recs:
            item = {k: v for k, v in rec.items() if k != "safety_info"}
            safety = rec.get("safety_info") or recommender.get_safety_info(rec["exercise_id"])
            item["recommended_intensity"] = safety.get("recommended_intensity")
            item["safe_duration"] = safety.get("safe_duration")
            item["best_exercise_type"] = safety.get("best_exercise_type")
            item["safety_notes"] = safety.get("notes")
            item["is_unsafe"] = safety.get("unsafe", False)
            export_recs.append(item)

        export_df = pd.DataFrame(export_recs)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                label="📥 Download CSV",
                data=export_df.to_csv(index=False),
                file_name=f"{user_id}_{rec_mode}_workout.csv",
                mime="text/csv",
                use_container_width=True
            )
        with dl2:
            st.download_button(
                label="📥 Download JSON",
                data=json.dumps(export_recs, indent=2, default=str),
                file_name=f"{user_id}_{rec_mode}_workout.json",
                mime="application/json",
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("📝 Exercise Details, Ratings & Completion")
        _render_recommendation_cards(recommender, recs, prefix=f"{user_id}_{rec_mode}")


def exercises_ui(sys_obj: RecommendationSystem):
    st.header("📚 Exercise Catalog")
    exs = sys_obj.exercise_db.get_all_exercises()

    f1, f2 = st.columns(2)
    with f1:
        diff_filter = st.multiselect(
            "Filter by Difficulty",
            ["BEGINNER", "INTERMEDIATE", "ADVANCED"],
            default=["BEGINNER", "INTERMEDIATE", "ADVANCED"]
        )
    with f2:
        search_query = st.text_input("Search by Exercise Name or Muscle", placeholder="e.g. squats, chest, cardio")

    rows = []
    for e in exs:
        if e.difficulty.name not in diff_filter:
            continue
        muscles_str = ", ".join(m.value for m in e.primary_muscles)
        if search_query:
            q = search_query.strip().lower()
            if q not in e.name.lower() and q not in muscles_str.lower() and q not in e.description.lower():
                continue
        rows.append({
            "ID": e.exercise_id,
            "Name": e.name,
            "Difficulty": e.difficulty.name,
            "Primary Muscles": muscles_str,
            "Duration (min)": e.duration_minutes,
            "Intensity": f"{e.intensity_level}/10",
            "Calories/min": e.calories_burned,
            "Sets": e.sets,
            "Reps": e.reps,
            "Equipment": ", ".join(e.equipment_required) if e.equipment_required else "Bodyweight",
            "Contraindications": ", ".join(e.contraindications) if e.contraindications else "None"
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        st.download_button(
            label="📥 Download Filtered Exercises CSV",
            data=df.to_csv(index=False),
            file_name="exercises_catalog.csv",
            mime="text/csv"
        )


def _start_process(name: str, args: list):
    """Start a background process and capture stdout/stderr safely."""
    key_proc = f"proc_{name}"
    key_log = f"log_{name}"
    existing = st.session_state.get(key_proc)
    if existing is not None and existing.poll() is None:
        return False, f"{name} is already running"

    try:
        proc = subprocess.Popen(
            [sys.executable] + args,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    except Exception as e:
        return False, f"Failed to start {name}: {e}"

    st.session_state[key_proc] = proc
    st.session_state[key_log] = ""
    proc._logs = []

    def _reader():
        try:
            for line in proc.stdout:
                proc._logs.append(line)
        except Exception as e:
            proc._logs.append(f"\n[reader-error] {e}\n")

    threading.Thread(target=_reader, daemon=True).start()
    return True, f"Started {name}"


def _stop_process(name: str):
    """Stop a running background process."""
    key_proc = f"proc_{name}"
    key_log = f"log_{name}"
    proc = st.session_state.get(key_proc)
    if not proc:
        return False, f"{name} is not running"
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception as e:
            return False, f"Failed to stop {name}: {e}"
    st.session_state[key_proc] = None
    st.session_state[key_log] = "".join(getattr(proc, "_logs", [])) + "\n[process stopped]\n"
    return True, f"Stopped {name}"


def admin_ui(sys_obj: RecommendationSystem):
    """Admin dashboard with system status, user management, and background process controls."""
    st.header("🔧 Admin Dashboard")
    st.markdown("**System management, user data export/cleanup, and background services**")

    status_col1, status_col2, status_col3, status_col4 = st.columns(4)

    with status_col1:
        num_users = len(sys_obj.user_manager.profiles)
        st.metric("Users Registered", num_users)
        st.success("✅ Active") if num_users > 0 else st.warning("⚠️ No users yet")

    with status_col2:
        if MODEL_FILE.exists():
            size_mb = round(MODEL_FILE.stat().st_size / (1024 * 1024), 2)
            st.metric("RL Model", f"{size_mb} MB")
            st.success("✅ Loaded")
        else:
            st.metric("RL Model", "Untrained")
            st.warning("⚠️ trained_agent.pt missing")

    with status_col3:
        hist_files = list(DATA_DIR.glob("*_history.json")) if DATA_DIR.exists() else []
        st.metric("History Files", len(hist_files))
        st.success("✅ Data available") if hist_files else st.info("ℹ️ No history yet")

    with status_col4:
        exercise_count = len(sys_obj.exercise_db.exercises)
        st.metric("Exercises", exercise_count)
        st.success("✅ Catalog ready") if exercise_count > 0 else st.error("❌ Empty catalog")

    st.markdown("---")
    st.subheader("👥 User Management")

    if sys_obj.user_manager.profiles:
        user_list = list(sys_obj.user_manager.profiles.keys())
        selected_user = st.selectbox("Select user to manage", user_list, key="admin_user_select")

        if selected_user:
            profile = sys_obj.user_manager.profiles[selected_user]
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**User ID:** {profile.user_id}")
                st.write(f"**Age:** {profile.age}")
                st.write(f"**Fitness Level:** {profile.fitness_level.name}")
                st.write(f"**Available Time:** {profile.available_time} minutes")
            with col2:
                st.write(f"**Goals:** {', '.join([g.value for g in profile.goals])}")
                st.write(f"**Equipment:** {', '.join(profile.equipment_access) if profile.equipment_access else 'Bodyweight only'}")
                st.write(f"**Injuries:** {', '.join(profile.injuries) if profile.injuries else 'None'}")

            user_history_file = DATA_DIR / f"{selected_user}_history.json"
            if user_history_file.exists():
                try:
                    with open(user_history_file, "r", encoding="utf-8") as f:
                        user_data = json.load(f)

                    rec_count = len(user_data.get("recommendation_history", []))
                    feedback_count = len(user_data.get("user_feedback", {}))
                    st.info(f"📊 {rec_count} history entries • {feedback_count} feedback ratings")

                    dl_col, del_col = st.columns(2)
                    with dl_col:
                        st.download_button(
                            label=f"📥 Download {selected_user} JSON",
                            data=json.dumps(user_data, indent=2),
                            file_name=f"{selected_user}_history.json",
                            mime="application/json",
                            key=f"dl_{selected_user}",
                            use_container_width=True
                        )

                    with del_col:
                        confirm_del = st.checkbox(f"Confirm permanent deletion of {selected_user}'s history", key=f"chk_del_{selected_user}")
                        if st.button(f"🗑️ Delete {selected_user} History", disabled=not confirm_del, key=f"del_{selected_user}", use_container_width=True):
                            user_history_file.unlink()
                            if selected_user in sys_obj.recommenders:
                                sys_obj.recommenders[selected_user].recommendation_history = []
                                sys_obj.recommenders[selected_user].user_feedback = {}
                            st.success(f"✅ Deleted history for {selected_user}")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error reading user data: {e}")
            else:
                st.info(f"No history file saved yet for {selected_user}.")
    else:
        st.info("No users registered yet.")

    st.markdown("---")
    st.subheader("📁 Bulk Data Operations")
    b1, b2 = st.columns(2)

    with b1:
        combined = {}
        if DATA_DIR.exists():
            for p in DATA_DIR.glob("*_history.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        combined[p.stem] = json.load(f)
                except Exception as e:
                    combined[p.stem] = {"error": str(e)}

        if combined:
            st.download_button(
                label="📄 Download All User Histories (JSON)",
                data=json.dumps(combined, indent=2),
                file_name=f"all_user_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        else:
            st.info("No history files available to export.")

    with b2:
        if st.button("🧹 Clean Empty History Files", use_container_width=True):
            cleaned = 0
            if DATA_DIR.exists():
                for p in DATA_DIR.glob("*_history.json"):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if not data.get("recommendation_history") and not data.get("user_feedback"):
                            p.unlink()
                            cleaned += 1
                    except Exception:
                        pass
            st.success(f"Cleaned {cleaned} empty history file(s).")

    st.markdown("---")
    st.subheader("⚙️ Background Processes & Logs")

    process_tabs = st.tabs(["🤖 Training", "🌐 Flask API Server", "🧪 Automated Tests"])

    with process_tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start Training (50 episodes)", key="start_training"):
                script = "train_simple.py" if (ROOT_DIR / "train_simple.py").exists() else "trainer.py"
                started, msg = _start_process("training", [script]) if (ROOT_DIR / script).exists() else (False, "Training script not found")
                st.success(msg) if started else st.error(msg)
        with col2:
            if st.button("⏹️ Stop Training", key="stop_training"):
                stopped, msg = _stop_process("training")
                st.success(msg) if stopped else st.info(msg)

    with process_tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start API Server (Port 5000)", key="start_api"):
                started, msg = _start_process("api", ["api.py"]) if (ROOT_DIR / "api.py").exists() else (False, "api.py not found")
                st.success(msg) if started else st.error(msg)
        with col2:
            if st.button("⏹️ Stop API Server", key="stop_api"):
                stopped, msg = _stop_process("api")
                st.success(msg) if stopped else st.info(msg)

    with process_tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧪 Run Timed Recommendation Test", key="run_timed_test"):
                started, msg = _start_process("smoke_timed", ["test_timed_recommendations.py"]) if (ROOT_DIR / "test_timed_recommendations.py").exists() else (False, "test_timed_recommendations.py not found")
                st.success(msg) if started else st.error(msg)
        with col2:
            if st.button("🧪 Run Smoke Test", key="run_multi_test"):
                started, msg = _start_process("smoke_multi", ["quick_smoke_test.py"]) if (ROOT_DIR / "quick_smoke_test.py").exists() else (False, "quick_smoke_test.py not found")
                st.success(msg) if started else st.error(msg)

    logs_tabs = st.tabs(["Training Logs", "API Logs", "Timed Test Logs", "Smoke Test Logs"])
    for tab, name in zip(logs_tabs, ["training", "api", "smoke_timed", "smoke_multi"]):
        with tab:
            proc = st.session_state.get(f"proc_{name}")
            log_text = "".join(proc._logs) if (proc and hasattr(proc, "_logs")) else st.session_state.get(f"log_{name}", "")
            if log_text:
                st.text_area(f"Output ({name})", value=log_text, height=220, disabled=True, key=f"ta_{name}")
            else:
                st.info(f"No logs captured yet for {name}.")

    with st.expander("ℹ️ Environment Details"):
        st.write(f"**Python Version:** {platform.python_version()}")
        st.write(f"**Platform:** {platform.platform()}")
        st.write(f"**Project Directory:** {ROOT_DIR}")
        if importlib.util.find_spec("psutil") is not None:
            psutil = importlib.import_module("psutil")
            mem = psutil.virtual_memory()
            st.write(f"**Memory Usage:** {mem.percent}% ({round(mem.used / 1024 / 1024)} MB used)")


def metrics_ui(sys_obj: RecommendationSystem):
    st.header("📊 System Metrics & Catalog Overview")

    exs = sys_obj.exercise_db.get_all_exercises()
    ex_df = pd.DataFrame([
        {
            "exercise_id": e.exercise_id,
            "name": e.name,
            "difficulty": e.difficulty.name,
            "intensity": e.intensity_level,
        }
        for e in exs
    ])

    st.subheader("📋 Exercise Catalog Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Exercises", len(exs))
    c2.metric("Beginner", len(ex_df[ex_df["difficulty"] == "BEGINNER"]) if not ex_df.empty else 0)
    c3.metric("Intermediate", len(ex_df[ex_df["difficulty"] == "INTERMEDIATE"]) if not ex_df.empty else 0)
    c4.metric("Advanced", len(ex_df[ex_df["difficulty"] == "ADVANCED"]) if not ex_df.empty else 0)

    if not ex_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Difficulty Breakdown**")
            st.bar_chart(ex_df["difficulty"].value_counts())
        with col2:
            st.write("**Intensity Levels**")
            st.bar_chart(ex_df["intensity"].value_counts().sort_index())

    st.markdown("---")
    st.subheader("🦵 Muscle Group Coverage")
    muscle_groups = {}
    for e in exs:
        for muscle in e.primary_muscles:
            m_str = muscle.value if hasattr(muscle, "value") else str(muscle)
            muscle_groups[m_str] = muscle_groups.get(m_str, 0) + 1

    if muscle_groups:
        muscle_df = pd.DataFrame(
            list(muscle_groups.items()),
            columns=["Muscle Group", "Exercises"]
        ).sort_values("Exercises", ascending=False)
        st.bar_chart(muscle_df.set_index("Muscle Group"))

    st.markdown("---")
    st.subheader("📈 Global Recommendation & Feedback Statistics")

    total_recommendations = 0
    total_feedbacks = 0
    feedback_data = []

    for uid in sys_obj.user_manager.profiles.keys():
        history_file = DATA_DIR / f"{uid}_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                recs = history.get("recommendation_history", [])
                user_feedback = history.get("user_feedback", {})
                total_recommendations += len(recs)

                if user_feedback:
                    total_feedbacks += len(user_feedback)
                    for ex_id, score in user_feedback.items():
                        feedback_data.append({"Exercise": ex_id, "Score": float(score), "User": uid})
                else:
                    for rec in recs:
                        ex_id = rec.get("exercise_id")
                        score = rec.get("simulated_satisfaction")
                        if ex_id and score is not None:
                            total_feedbacks += 1
                            feedback_data.append({"Exercise": ex_id, "Score": float(score), "User": uid})
            except Exception:
                pass

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Logged Recommendations", total_recommendations)
    m2.metric("Total Rated Exercises", total_feedbacks)
    rate = (total_feedbacks / total_recommendations * 100) if total_recommendations > 0 else 0.0
    m3.metric("Feedback Coverage", f"{rate:.1f}%")

    if feedback_data:
        feedback_df = pd.DataFrame(feedback_data)
        avg_scores = feedback_df.groupby("Exercise")["Score"].mean().sort_values(ascending=False).head(10)
        st.write("**Top Rated Exercises (Average Score)**")
        st.bar_chart(avg_scores)
    else:
        st.info("No feedback scores recorded yet.")


def analytics_ui(sys_obj: RecommendationSystem):
    """User-level daily, weekly, and 30-day progress analytics."""
    st.header("📈 Exercise Analytics Dashboard")

    analytics = ExerciseAnalytics(str(DATA_DIR), system=sys_obj)
    profiles = list(sys_obj.user_manager.profiles.keys())

    if not profiles:
        st.info("No users registered yet. Register a user first.")
        return

    user_id = st.selectbox("Select User for Analytics", profiles, key="analytics_user")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Today's Summary",
        "Weekly Progress",
        "30-Day Trends",
        "Time Patterns",
        "Effectiveness",
        "User Comparison"
    ])

    with tab1:
        st.subheader("Today's Exercise Summary")
        daily = analytics.get_user_daily_summary(user_id)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Exercises", daily["total_exercises"])
        c2.metric("Sessions", daily["total_sessions"])
        c3.metric("Duration", f"{daily['total_duration_minutes']} min")
        c4.metric("Calories", f"{int(daily['total_calories_burned'])} kcal")

        if daily.get("exercises"):
            ex_df = pd.DataFrame([
                {
                    "Exercise": e["name"],
                    "Duration (min)": e["duration"],
                    "Calories": round(e["calories"], 1),
                    "Intensity": e["intensity"],
                    "Satisfaction": f"{e['satisfaction']:.1f}/10"
                }
                for e in daily["exercises"]
            ])
            st.dataframe(ex_df, use_container_width=True, hide_index=True)

            if daily.get("muscles_worked"):
                st.write("**🏋️ Muscles Targeted Today**")
                m_df = pd.DataFrame(list(daily["muscles_worked"].items()), columns=["Muscle", "Count"])
                st.bar_chart(m_df.set_index("Muscle"))
        else:
            st.info("No exercises logged for today yet.")

    with tab2:
        st.subheader("Last 7 Days Summary")
        weekly = analytics.get_weekly_summary(user_id, days_back=7)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Days Active", weekly["days_active"])
        c2.metric("Activity Rate", f"{weekly['activity_rate']}%")
        c3.metric("Exercises", weekly["total_exercises"])
        c4.metric("Total Duration", f"{weekly['total_duration_minutes']:.0f} min")
        c5.metric("Calories", f"{int(weekly['total_calories_burned'])} kcal")

        if weekly.get("daily_summaries"):
            daily_df = pd.DataFrame([
                {
                    "date": d["date"],
                    "exercises": d["total_exercises"],
                    "duration": d["total_duration_minutes"],
                    "calories": d["total_calories_burned"],
                    "satisfaction": d["average_satisfaction"]
                }
                for d in weekly["daily_summaries"]
            ])
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Daily Exercises & Duration**")
                st.line_chart(daily_df.set_index("date")[["exercises", "duration"]])
            with col2:
                st.write("**Daily Calories & Satisfaction**")
                st.line_chart(daily_df.set_index("date")[["calories", "satisfaction"]])

    with tab3:
        st.subheader("30-Day Progress Trends")
        progress = analytics.get_progress_metrics(user_id, days_back=30)

        if progress:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Sessions", progress["total_sessions"])
            c2.metric("Session Frequency", f"{progress['session_frequency']}%")
            c3.metric("Avg Duration", f"{progress['average_session_duration']:.0f} min")
            c4.metric("Avg Intensity", f"{progress['average_session_intensity']:.1f}/10")
            c5.metric("Avg Satisfaction", f"{progress['average_satisfaction']:.1f}/10")

            s1, s2 = st.columns(2)
            s1.metric("Current Streak", f"{progress['streak_current']} days")
            s2.metric("Longest Streak", f"{progress['streak_longest']} days")

            trend_map = {"positive": "Improving 📈", "negative": "Declining 📉", "stable": "Stable →"}
            trend_df = pd.DataFrame([
                {"Metric": "Duration", "Trend": trend_map.get(progress["duration_trend"], "Stable")},
                {"Metric": "Intensity", "Trend": trend_map.get(progress["intensity_trend"], "Stable")},
                {"Metric": "Satisfaction", "Trend": trend_map.get(progress["satisfaction_trend"], "Stable")},
            ])
            st.dataframe(trend_df, use_container_width=True, hide_index=True)
        else:
            st.info("Not enough 30-day history available yet.")

    with tab4:
        st.subheader("⏰ Workout Time Patterns (30 Days)")
        time_analysis = analytics.get_time_analysis(user_id, days_back=30)

        if time_analysis:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sessions Analyzed", time_analysis["total_sessions_analyzed"])
            c2.metric("Peak Hour", time_analysis["peak_hour"])
            c3.metric("Peak Sessions", time_analysis["peak_hour_sessions"])
            c4.metric("Most Active Day", time_analysis.get("most_active_day") or "N/A")

            time_dist = time_analysis["time_distribution"]
            values = [time_dist["morning"], time_dist["afternoon"], time_dist["evening"], time_dist["night"]]
            if sum(values) > 0:
                fig, ax = plt.subplots(figsize=(5, 3.5))
                ax.pie(
                    values,
                    labels=["Morning", "Afternoon", "Evening", "Night"],
                    autopct="%1.1f%%",
                    startangle=90
                )
                ax.axis("equal")
                st.pyplot(fig)
                plt.close(fig)

            hourly = time_analysis["hourly_breakdown"]
            hour_df = pd.DataFrame({
                "Hour": [f"{h:02d}:00" for h in range(24)],
                "Sessions": [hourly.get(h, 0) for h in range(24)]
            })
            st.bar_chart(hour_df.set_index("Hour"))
        else:
            st.info("No workout timestamp data available yet.")

    with tab5:
        st.subheader("Recommendation Effectiveness & Safety")
        rec_analysis = analytics.get_exercise_recommendations_analysis(user_id)

        if rec_analysis:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Recommendations", rec_analysis["total_recommendations"])
            c2.metric("Unique / Completed", rec_analysis["total_completions"])
            c3.metric("Acceptance Rate", f"{rec_analysis['acceptance_rate']:.1f}%")
            c4.metric("Avg Satisfaction", f"{rec_analysis['average_satisfaction']:.1f}/10")

            if rec_analysis.get("top_rated_exercises"):
                top_df = pd.DataFrame(rec_analysis["top_rated_exercises"], columns=["Exercise ID", "Avg Rating"])
                st.bar_chart(top_df.set_index("Exercise ID"))
        else:
            st.info("No recommendation history yet.")

        injury_analysis = analytics.get_injury_impact_analysis(user_id)
        if injury_analysis.get("injuries"):
            st.markdown("---")
            st.write(f"**Active Constraints:** {', '.join(injury_analysis['injuries'])}")
            st.write(f"**Safe Exercises Logged:** {injury_analysis.get('safe_exercise_count', 0)}")

    with tab6:
        st.subheader("Compare Users")
        compare_users = st.multiselect(
            "Select at least 2 users to compare",
            profiles,
            default=profiles[:2] if len(profiles) >= 2 else profiles,
            key="compare_users_select"
        )

        if len(compare_users) >= 2:
            comparison = analytics.get_comparison_metrics(compare_users, days_back=7)
            if comparison.get("user_metrics"):
                comp_df = pd.DataFrame([
                    {
                        "User": uid,
                        "Activity Rate (%)": m["activity_rate"],
                        "Total Exercises": m["total_exercises"],
                        "Duration (min)": m["total_duration"],
                        "Days Active": m["days_active"]
                    }
                    for uid, m in comparison["user_metrics"].items()
                ])
                st.dataframe(comp_df, use_container_width=True, hide_index=True)
        else:
            st.info("Select 2 or more users to view side-by-side metrics.")


def main():
    st.set_page_config(
        page_title="RL Exercise Recommendation System",
        page_icon="🏋️",
        layout="wide"
    )
    st.title("🏋️ RL-Based Exercise Recommendation Dashboard")
    st.sidebar.title("Navigation")

    sys_obj = get_system()

    view = st.sidebar.radio(
        "Go to",
        ["Recommendations", "Register User", "Exercises", "Analytics", "Metrics", "Admin"],
        index=0
    )

    if view == "Recommendations":
        recommendations_ui(sys_obj)
    elif view == "Register User":
        user_registration_ui(sys_obj)
    elif view == "Exercises":
        exercises_ui(sys_obj)
    elif view == "Analytics":
        analytics_ui(sys_obj)
    elif view == "Metrics":
        metrics_ui(sys_obj)
    elif view == "Admin":
        admin_ui(sys_obj)


if __name__ == "__main__":
    main()