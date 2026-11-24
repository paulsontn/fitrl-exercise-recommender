"""
Streamlit dashboard for Exercise Recommendation System

Run with:
    streamlit run streamlit_dashboard.py

Features:
- Register a new user via a simple form
- Select an existing user and request recommendations
- View exercises table
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import sys
import threading
import subprocess
from exercise_analytics_v2 import ExerciseAnalytics
import time
from pathlib import Path
import importlib.util
from datetime import datetime
from recommendation_system import RecommendationSystem
from user_profile import FitnessLevel, UserGoal, UserProfile


@st.cache_resource
def get_system():
    # Instantiate recommendation system (loads trained agent if present)
    return RecommendationSystem(agent_path="trained_agent.pt")


def user_registration_ui(sys: RecommendationSystem):
    st.header("Register New User")
    st.markdown("Fill out your profile to get personalized exercise recommendations tailored to your fitness level, available equipment, and goals.")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            user_id = st.text_input("User ID", value=f"user_{len(sys.user_manager.profiles)+1}")
            age = st.number_input("Age", min_value=13, max_value=100, value=30)
            fitness_level = st.selectbox("Fitness Level", [f.name for f in FitnessLevel])
        
        with col2:
            goals_mult = st.multiselect("Goals", [g.value for g in UserGoal], default=[UserGoal.GENERAL_FITNESS.value])
            available_time = st.number_input("Available time (minutes)", min_value=5, max_value=180, value=45)
        
        st.markdown("**Equipment & Exercise Preferences**")
        equipment = st.text_input(
            "Available Equipment (comma separated)",
            value="",
            placeholder="e.g. dumbbells, kettlebell, mat, bench, barbell, resistance bands",
            help="List the equipment you have access to. Leave blank if you prefer bodyweight exercises only."
        )
        
        st.markdown("### 📋 Equipment Ideas:")
        st.markdown("""
        - Bodyweight (no equipment needed): Walking, Yoga, Push-ups, Crunches, Planks
        - Dumbbells: Bicep Curls, Dumbbell Rows, Shoulder Press
        - Mat: Yoga, Stretching, Core exercises
        - Kettlebell: Full-body workouts
        - Barbell: Strength training
        - Resistance Bands: Low-impact training
        """)
        
        preferred = st.text_input(
            "Preferred Exercises (comma separated, optional)",
            placeholder="e.g. running, yoga, weightlifting"
        )

        # Daily condition inputs
        st.markdown("**Daily conditions (optional)**")
        col1, col2 = st.columns(2)
        with col1:
            fatigue = st.slider("Fatigue (0 = rested, 10 = exhausted)", 0.0, 10.0, 0.0)
            soreness = st.slider("Soreness (0 = none, 10 = very sore)", 0.0, 10.0, 0.0)
        with col2:
            sleep_hours = st.number_input("Sleep hours (last night)", min_value=0.0, max_value=24.0, value=8.0)
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=200, value=60)

        submitted = st.form_submit_button("Register")
        if submitted:
            goals = [UserGoal(g) if isinstance(g, str) and g in [x.value for x in UserGoal] else UserGoal.GENERAL_FITNESS for g in goals_mult]
            # map selection string back to enum
            try:
                fitness_enum = FitnessLevel[fitness_level]
            except Exception:
                fitness_enum = FitnessLevel.BEGINNER

            profile = UserProfile(
                user_id=user_id,
                age=int(age),
                fitness_level=fitness_enum,
                goals=[UserGoal(g) for g in goals_mult] if goals_mult else [UserGoal.GENERAL_FITNESS],
                available_time=int(available_time),
                injuries=[],
                equipment_access=[e.strip() for e in equipment.split(",") if e.strip()],
                preferred_exercises=[p.strip() for p in preferred.split(",") if p.strip()],
                fatigue=float(fatigue),
                soreness=float(soreness),
                sleep_hours=float(sleep_hours),
                resting_heart_rate=int(resting_hr)
            )
            sys.register_user(profile)
            
            # Show what was registered
            st.success(f"✅ Registered user {user_id}")
            st.info(f"**Equipment registered:** {', '.join(profile.equipment_access) if profile.equipment_access else 'Bodyweight only'}")
            st.info(f"**Suitable exercises available:** {len(sys.get_recommender(user_id).suitable_exercises)} exercises")


def recommendations_ui(sys: RecommendationSystem):
    st.header("Recommendations")
    profiles = list(sys.user_manager.profiles.keys())
    if not profiles:
        st.info("No users registered yet. Register a user first.")
        return

    user_id = st.selectbox("Select user", profiles)
    recommender = sys.get_recommender(user_id)
    profile = recommender.user_profile
    
    # Display user profile information including equipment
    st.subheader("📋 User Profile")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Age", profile.age)
    with col2:
        st.metric("Fitness Level", profile.fitness_level.name)
    with col3:
        st.metric("Available Time", f"{profile.available_time} min")
    with col4:
        st.metric("Suitable Exercises", len(recommender.suitable_exercises))
    
    # Equipment information
    st.markdown("---")
    st.subheader("🛠️ Available Equipment & Injuries")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Available Equipment:**")
        if profile.equipment_access:
            for eq in profile.equipment_access:
                st.write(f"  • {eq}")
        else:
            st.write("  *No equipment (bodyweight only)*")
    
    with col2:
        st.write("**Injuries/Constraints:**")
        if profile.injuries:
            for inj in profile.injuries:
                st.write(f"  • {inj}")
        else:
            st.write("  *No constraints*")
    
    st.info(f"📝 **{len(recommender.suitable_exercises)}** exercises are recommended for this user based on their fitness level, available equipment, and injury constraints.")
    
    st.markdown("---")
    
    # Get user's available time
    available_time = profile.available_time
    
    mode = st.radio("Recommendation Mode", ["Fit to Available Time", "Top N Recommendations"])
    
    if mode == "Fit to Available Time":
        exploration = st.checkbox("Use exploration (randomness)")
        if st.button("Get Timed Workout"):
            try:
                recs = recommender.get_recommendations(available_time_minutes=available_time, use_exploration=exploration)
                if not recs:
                    st.warning("No recommendations available for this user.")
                    return
                
                # Calculate totals
                total_duration = sum(r['duration_minutes'] for r in recs)
                total_calories = sum(r.get('total_calories', 0) for r in recs)
                
                st.success(f"✅ Workout created: {total_duration} minutes, {total_calories:.0f} calories")
                
                df = pd.DataFrame(recs)
                st.dataframe(df)
                
                # Export with safety metadata
                try:
                    export_recs = []
                    for rec in recs:
                        export_rec = rec.copy()
                        try:
                            safety = recommender.get_safety_info(rec['exercise_id'])
                            export_rec['recommended_intensity'] = safety.get('recommended_intensity')
                            export_rec['safe_duration'] = safety.get('safe_duration')
                            export_rec['best_exercise_type'] = safety.get('best_exercise_type')
                            export_rec['safety_notes'] = safety.get('notes')
                            export_rec['is_unsafe'] = safety.get('unsafe', False)
                        except Exception:
                            export_rec['recommended_intensity'] = None
                            export_rec['safe_duration'] = None
                            export_rec['best_exercise_type'] = None
                            export_rec['safety_notes'] = None
                            export_rec['is_unsafe'] = False
                        export_recs.append(export_rec)
                    
                    export_df = pd.DataFrame(export_recs)
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV (timed workout with safety data)",
                        data=csv,
                        file_name=f"{user_id}_timed_workout.csv",
                        mime='text/csv'
                    )
                    
                    json_str = json.dumps(export_recs, indent=2, default=str)
                    st.download_button(
                        label="📥 Download JSON (timed workout with safety data)",
                        data=json_str,
                        file_name=f"{user_id}_timed_workout.json",
                        mime='application/json'
                    )
                except Exception as e:
                    st.warning(f"Export not fully available: {e}")
            except Exception as e:
                st.error(f"Error getting recommendations: {e}")
    else:
        num_recs = st.slider("Number of recommendations", 1, 30, 30)
        exploration = st.checkbox("Use exploration (randomness)")
        
        if st.button("Get Recommendations"):
            try:
                recs = recommender.get_recommendations(num_recommendations=num_recs, use_exploration=exploration)
                if not recs:
                    st.warning("No recommendations available for this user.")
                    return

                df = pd.DataFrame(recs)
                st.dataframe(df)

                # Export buttons: CSV and JSON with safety metadata
                try:
                    # Add safety metadata to each recommendation for export
                    export_recs = []
                    for rec in recs:
                        export_rec = rec.copy()
                        try:
                            safety = recommender.get_safety_info(rec['exercise_id'])
                            export_rec['recommended_intensity'] = safety.get('recommended_intensity')
                            export_rec['safe_duration'] = safety.get('safe_duration')
                            export_rec['best_exercise_type'] = safety.get('best_exercise_type')
                            export_rec['safety_notes'] = safety.get('notes')
                            export_rec['is_unsafe'] = safety.get('unsafe', False)
                        except Exception:
                            export_rec['recommended_intensity'] = None
                            export_rec['safe_duration'] = None
                            export_rec['best_exercise_type'] = None
                            export_rec['safety_notes'] = None
                            export_rec['is_unsafe'] = False
                        export_recs.append(export_rec)
                    
                    export_df = pd.DataFrame(export_recs)
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV (with safety data)",
                        data=csv,
                        file_name=f"{user_id}_recommendations.csv",
                        mime='text/csv'
                    )

                    json_str = json.dumps(export_recs, indent=2, default=str)
                    st.download_button(
                        label="📥 Download JSON (with safety data)",
                        data=json_str,
                        file_name=f"{user_id}_recommendations.json",
                        mime='application/json'
                    )
                except Exception as e:
                    st.warning(f"Export not available: {e}")

                # Show rationale and allow feedback
                for i, rec in enumerate(recs):
                    # Use unique widget keys by appending the index to avoid duplicate-key errors
                    slider_key = f"{rec['exercise_id']}_{i}_score"
                    btn_key = f"fb_{rec['exercise_id']}_{i}"
                    with st.expander(f"{rec['exercise_name']} (id: {rec['exercise_id']})"):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write("**Duration:**")
                            st.write(f"{rec['duration_minutes']} min")
                        with col2:
                            st.write("**Intensity:**")
                            st.write(f"{rec['intensity_level']}/10")
                        with col3:
                            st.write("**Calories/min:**")
                            st.write(f"{rec['calories_burned']}")
                        with col4:
                            st.write("**Total Calories:**")
                            total_cals = rec.get('total_calories', rec['duration_minutes'] * rec['calories_burned'])
                            st.write(f"{total_cals:.0f}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write("**Sets:**")
                            st.write(rec['sets'])
                        with col2:
                            st.write("**Reps/Duration:**")
                            st.write(rec['reps'])
                        with col3:
                            st.write("**Equipment:**")
                            st.write(", ".join(rec['equipment_required']) if rec['equipment_required'] else "None")
                        
                        # Compute safety and recommendation metadata
                        try:
                            safety = recommender.get_safety_info(rec['exercise_id'])
                            st.write("**Best Type:**", safety.get('best_exercise_type'))
                            st.write("**Recommended Intensity:**", f"{safety.get('recommended_intensity')}/10")
                            st.write("**Safe Duration:**", f"{safety.get('safe_duration')} min")
                            if safety.get('unsafe'):
                                st.warning(f"Safety note: {safety.get('notes')}")
                            else:
                                st.info(safety.get('notes'))
                        except Exception:
                            pass

                        st.write(rec['description'])
                        st.write("Rationale:", rec['rationale'])
                        score = st.slider(f"Satisfaction for {rec['exercise_id']}", 0.0, 10.0, 5.0, key=slider_key)
                        if st.button(f"Submit feedback {rec['exercise_id']}", key=btn_key):
                            # Record feedback for the base exercise id (overwrites previous if repeated)
                            recommender.provide_feedback(rec['exercise_id'], float(score))
                            st.success("Feedback recorded")

                        # Mark as completed button (records reward entry)
                        complete_key = f"complete_{rec['exercise_id']}_{i}"
                        if st.button("Mark completed", key=complete_key):
                            try:
                                entry = recommender.record_completion(rec['exercise_id'], satisfaction_score=float(score))
                                st.success(f"Recorded completion: reward={entry.get('reward')}, satisfaction={entry.get('satisfaction')}")
                            except Exception as e:
                                st.error(f"Failed to record completion: {e}")
            except Exception as e:
                st.error(f"Error getting recommendations: {e}")


def exercises_ui(sys: RecommendationSystem):
    st.header("Exercise Catalog")
    exs = sys.exercise_db.get_all_exercises()
    rows = []
    for e in exs:
        rows.append({
            'exercise_id': e.exercise_id,
            'name': e.name,
            'difficulty': e.difficulty.name,
            'duration_minutes': e.duration_minutes,
            'intensity_level': e.intensity_level,
            'sets': e.sets,
            'reps': e.reps,
            'equipment_required': ", ".join(e.equipment_required)
        })

    df = pd.DataFrame(rows)
    st.dataframe(df)
    
    # Export exercises
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Exercises CSV",
        data=csv,
        file_name="exercises_catalog.csv",
        mime='text/csv'
    )


def _start_process(name, args):
    """Start a background process and capture logs."""
    key_proc = f"proc_{name}"
    key_log = f"log_{name}"
    if key_proc in st.session_state and st.session_state[key_proc] is not None:
        return False, f"{name} already running"

    try:
        proc = subprocess.Popen([sys.executable] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        return False, f"Failed to start {name}: {e}"

    st.session_state[key_proc] = proc
    st.session_state.setdefault(key_log, "")

    # Store logs in a list that persists in the process object
    if not hasattr(proc, '_logs'):
        proc._logs = []

    def _reader():
        try:
            for line in proc.stdout:
                proc._logs.append(line)
        except Exception as e:
            proc._logs.append(f"\n[reader-error] {e}\n")

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    return True, f"Started {name}"


def _stop_process(name):
    """Stop a background process."""
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
    st.session_state[key_log] = "".join(getattr(proc, '_logs', [])) + "\n[process stopped]\n"
    return True, f"Stopped {name}"


def admin_ui(sys: RecommendationSystem):
    """Admin dashboard with project controls, file management, and logs."""
    st.header("🔧 Admin Dashboard")
    st.markdown("**System management, monitoring, and maintenance tools**")

    root = Path(__file__).parent
    data_dir = root / "data"
    model_file = root / "trained_agent.pt"

    # ===== SYSTEM STATUS =====
    st.subheader("📊 System Status")

    status_col1, status_col2, status_col3, status_col4 = st.columns(4)

    with status_col1:
        st.metric("**Users Registered**", len(sys.user_manager.profiles))
        if len(sys.user_manager.profiles) > 0:
            st.success("✅ Active")
        else:
            st.warning("⚠️ No users yet")

    with status_col2:
        if model_file.exists():
            size_mb = round(model_file.stat().st_size / (1024 * 1024), 2)
            st.metric("**AI Model**", f"{size_mb} MB")
            st.success("✅ Loaded")
        else:
            st.metric("**AI Model**", "Missing")
            st.error("❌ Not found")

    with status_col3:
        if data_dir.exists():
            hist_files = list(data_dir.glob("*_history.json"))
            st.metric("**History Files**", len(hist_files))
            if len(hist_files) > 0:
                st.success("✅ Data available")
            else:
                st.info("ℹ️ No data yet")
        else:
            st.metric("**Data Directory**", "Missing")
            st.warning("⚠️ Will be created")

    with status_col4:
        exercise_count = len(sys.exercise_db.exercises) if hasattr(sys, 'exercise_db') else 0
        st.metric("**Exercises**", exercise_count)
        if exercise_count > 0:
            st.success("✅ Database ready")
        else:
            st.error("❌ No exercises")

    st.markdown("---")

    # ===== USER MANAGEMENT =====
    st.subheader("👥 User Management")

    if sys.user_manager.profiles:
        user_list = list(sys.user_manager.profiles.keys())
        selected_user = st.selectbox("Select user to manage", user_list, key="admin_user_select")

        if selected_user:
            profile = sys.user_manager.profiles[selected_user]

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

            # User data management
            st.markdown("**Data Management:**")
            user_history_file = data_dir / f"{selected_user}_history.json"

            if user_history_file.exists():
                try:
                    with open(user_history_file, 'r') as f:
                        user_data = json.load(f)

                    rec_count = len(user_data.get('recommendation_history', []))
                    feedback_count = len(user_data.get('user_feedback', {}))

                    st.info(f"📊 {rec_count} recommendations, {feedback_count} feedback entries")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📥 Export {selected_user} data", key=f"export_{selected_user}"):
                            st.download_button(
                                f"Download {selected_user} data",
                                json.dumps(user_data, indent=2),
                                f"{selected_user}_history.json",
                                key=f"download_{selected_user}"
                            )

                    with col2:
                        if st.button(f"🗑️ Delete {selected_user} data", key=f"delete_{selected_user}"):
                            st.error("⚠️ This will permanently delete all user data!")
                            if st.button("CONFIRM DELETE", key=f"confirm_delete_{selected_user}"):
                                user_history_file.unlink()
                                st.success(f"✅ Deleted data for {selected_user}")
                                st.rerun()

                except Exception as e:
                    st.error(f"Error reading user data: {e}")
            else:
                st.warning(f"No data file found for {selected_user}")
    else:
        st.info("No users registered yet")

    st.markdown("---")

    # ===== FILE MANAGEMENT =====
    st.subheader("📁 File Management")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Project Files:**")
        py_files = sorted([p.name for p in root.iterdir() if p.is_file() and p.suffix == '.py'])
        for file in py_files:
            st.code(file, language="text")

        st.write("**Data Files:**")
        if data_dir.exists():
            json_files = sorted([p.name for p in data_dir.iterdir() if p.is_file() and p.suffix == '.json'])
            for file in json_files:
                st.code(file, language="text")
        else:
            st.info("No data directory")

    with col2:
        st.write("**Bulk Operations:**")

        if st.button("📥 Export ALL user data"):
            combined = {}
            if data_dir.exists():
                for p in data_dir.glob("*_history.json"):
                    try:
                        combined[p.stem] = json.load(open(p, "r", encoding="utf-8"))
                    except Exception as e:
                        combined[p.stem] = {"error": str(e)}

            if combined:
                st.download_button(
                    "📄 Download all user data",
                    json.dumps(combined, indent=2),
                    file_name=f"all_user_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
            else:
                st.info("No user data to export")

        if st.button("🧹 Clean empty data files"):
            cleaned = 0
            if data_dir.exists():
                for p in data_dir.glob("*_history.json"):
                    try:
                        data = json.load(open(p, "r", encoding="utf-8"))
                        if not data.get('recommendation_history') and not data.get('user_feedback'):
                            p.unlink()
                            cleaned += 1
                    except:
                        pass
            st.success(f"Cleaned {cleaned} empty files")

    st.markdown("---")

    # ===== SYSTEM PROCESSES =====
    st.subheader("⚙️ System Processes")

    process_tabs = st.tabs(["🤖 Training", "🌐 API Server", "🧪 Testing"])

    with process_tabs[0]:
        st.write("**AI Model Training**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start Training (50 episodes)", key="start_training"):
                started, msg = _start_process("training", ["train_simple.py", "--num_episodes", "50"]) if (root / "train_simple.py").exists() else (False, "train_simple.py not found")
                if started:
                    st.success("✅ Training started")
                else:
                    st.error(f"❌ {msg}")
        with col2:
            if st.button("⏹️ Stop Training", key="stop_training"):
                stopped, msg = _stop_process("training")
                if stopped:
                    st.success("✅ Training stopped")
                else:
                    st.info(msg)

    with process_tabs[1]:
        st.write("**API Server**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start API Server", key="start_api"):
                started, msg = _start_process("api", ["api.py"]) if (root / "api.py").exists() else (False, "api.py not found")
                if started:
                    st.success("✅ API server started")
                else:
                    st.error(f"❌ {msg}")
        with col2:
            if st.button("⏹️ Stop API Server", key="stop_api"):
                stopped, msg = _stop_process("api")
                if stopped:
                    st.success("✅ API server stopped")
                else:
                    st.info(msg)

    with process_tabs[2]:
        st.write("**System Testing**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧪 Run Timed Test", key="run_timed_test"):
                started, msg = _start_process("smoke_timed", ["test_timed_recommendations.py"]) if (root / "test_timed_recommendations.py").exists() else (False, "test not found")
                if started:
                    st.success("✅ Test started")
                else:
                    st.error(f"❌ {msg}")
        with col2:
            if st.button("🧪 Run Multi-Time Test", key="run_multi_test"):
                started, msg = _start_process("smoke_multi", ["test_multiple_times.py"]) if (root / "test_multiple_times.py").exists() else (False, "test not found")
                if started:
                    st.success("✅ Test started")
                else:
                    st.error(f"❌ {msg}")

    # ===== LIVE LOGS =====
    st.markdown("---")
    st.subheader("📋 Live Process Logs")

    logs_tabs = st.tabs(["Training Logs", "API Logs", "Test Logs (Timed)", "Test Logs (Multi)"])
    names = ["training", "api", "smoke_timed", "smoke_multi"]

    for t, name in zip(logs_tabs, names):
        with t:
            key_proc = f"proc_{name}"
            key_log = f"log_{name}"
            proc = st.session_state.get(key_proc)

            # Get logs from process object or session state
            if proc and hasattr(proc, '_logs'):
                log_text = "".join(proc._logs)
            else:
                log_text = st.session_state.get(key_log, "")

            if log_text:
                st.text_area(f"Live log: {name}", value=log_text, height=250, disabled=True)
            else:
                st.info(f"No logs available for {name}")

    # ===== SYSTEM INFO =====
    st.markdown("---")
    st.subheader("ℹ️ System Information")

    with st.expander("Environment Details"):
        import platform
        st.write(f"**Python Version:** {platform.python_version()}")
        st.write(f"**Platform:** {platform.platform()}")
        st.write(f"**Current Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**Working Directory:** {root}")

        # Memory usage if available
        psutil_spec = importlib.util.find_spec("psutil")
        if psutil_spec is not None:
            psutil = importlib.import_module("psutil")
            memory = psutil.virtual_memory()
            st.write(f"**Memory Usage:** {memory.percent}% ({round(memory.used/1024/1024)} MB used)")
        else:
            st.write("**Memory Usage:** Not available")


def metrics_ui(sys: RecommendationSystem):
    st.header("System Metrics & Visualizations")

    # Exercise distribution
    exs = sys.exercise_db.get_all_exercises()
    ex_rows = []
    for e in exs:
        ex_rows.append({
            'exercise_id': e.exercise_id,
            'name': e.name,
            'difficulty': e.difficulty.name,
            'intensity': e.intensity_level,
        })
    ex_df = pd.DataFrame(ex_rows)

    st.subheader("📋 Exercise Catalog Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Exercises", len(exs))
    with col2:
        beginner_count = len(ex_df[ex_df['difficulty'] == 'BEGINNER'])
        st.metric("Beginner", beginner_count)
    with col3:
        intermediate_count = len(ex_df[ex_df['difficulty'] == 'INTERMEDIATE'])
        st.metric("Intermediate", intermediate_count)
    with col4:
        advanced_count = len(ex_df[ex_df['difficulty'] == 'ADVANCED'])
        st.metric("Advanced", advanced_count)
    
    st.markdown("---")
    
    st.subheader("Exercise Distribution by Difficulty")
    if len(ex_df) > 0:
        col1, col2 = st.columns(2)
        with col1:
            counts = ex_df['difficulty'].value_counts()
            st.bar_chart(counts)
        with col2:
            intensity_dist = ex_df['intensity'].value_counts().sort_index()
            st.line_chart(intensity_dist)
    else:
        st.info("No exercises in database")

    st.markdown("---")
    
    # System Status
    st.subheader("⚙️ System Status")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Users Registered**")
        num_users = len(sys.user_manager.profiles)
        st.metric("Total Users", num_users)
        
        if num_users > 0:
            with st.expander("User Details"):
                user_data = []
                for uid, profile in sys.user_manager.profiles.items():
                    user_data.append({
                        'User ID': uid,
                        'Age': profile.age,
                        'Fitness Level': profile.fitness_level.name,
                        'Available Time': f"{profile.available_time} min"
                    })
                st.dataframe(pd.DataFrame(user_data), use_container_width=True)
    
    with col2:
        st.write("**Model Status**")
        model_file = Path(__file__).parent / "trained_agent.pt"
        if model_file.exists():
            st.success("✅ Model Loaded")
            st.metric("File Size", f"{model_file.stat().st_size / 1024:.1f} KB")
        else:
            st.warning("❌ Model Not Found")
            st.info("Run training to create the model")

    st.markdown("---")
    
    # User Activity Summary
    st.subheader("👥 User Activity Summary")
    
    if num_users > 0:
        activity_data = []
        for uid in sys.user_manager.profiles.keys():
            if uid in sys.recommenders:
                rec = sys.recommenders[uid]
                num_recs = len(rec.recommendation_history)
                num_feedbacks = len(rec.user_feedback)
                activity_data.append({
                    'User': uid,
                    'Recommendations': num_recs,
                    'Feedbacks Given': num_feedbacks,
                    'Top Exercise': max(rec.user_feedback.items(), key=lambda x: x[1])[0] if rec.user_feedback else 'N/A'
                })
        
        if activity_data:
            activity_df = pd.DataFrame(activity_data)
            st.dataframe(activity_df, use_container_width=True)
            
            # Charts
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Recommendations per User**")
                st.bar_chart(activity_df.set_index('User')[['Recommendations']])
            with col2:
                st.write("**Feedback Engagement**")
                st.bar_chart(activity_df.set_index('User')[['Feedbacks Given']])
        else:
            st.info("No user activity yet")
    else:
        st.info("Register a user first to see activity metrics")

    st.markdown("---")
    
    # Exercise Intensity Distribution
    st.subheader("💪 Exercise Intensity Profile")
    if len(ex_df) > 0:
        intensity_counts = ex_df['intensity'].value_counts().sort_index()
        st.bar_chart(intensity_counts)
        st.write(f"**Intensity Range:** {intensity_counts.index.min()}/10 to {intensity_counts.index.max()}/10")
    
    st.markdown("---")
    
    # Top Muscle Groups
    st.subheader("🦵 Muscle Groups Distribution")
    muscle_groups = {}
    for e in exs:
        for muscle in e.primary_muscles:
            muscle_str = muscle.value if hasattr(muscle, 'value') else str(muscle)
            muscle_groups[muscle_str] = muscle_groups.get(muscle_str, 0) + 1
    
    if muscle_groups:
        muscle_df = pd.DataFrame(
            list(muscle_groups.items()),
            columns=['Muscle Group', 'Exercises']
        ).sort_values('Exercises', ascending=False)
        st.bar_chart(muscle_df.set_index('Muscle Group'))
    
    st.markdown("---")
    
    # Recommender Statistics
    st.subheader("📊 Recommendation Statistics")

    total_recommendations = 0
    total_feedbacks = 0
    feedback_data = []

    # Load data from history files for all users
    for uid in sys.user_manager.profiles.keys():
        history_file = Path("data") / f"{uid}_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    recs = history.get('recommendation_history', [])
                    user_feedback = history.get('user_feedback', {})
                    
                    total_recommendations += len(recs)
                    
                    # Use user_feedback if available, otherwise use simulated_satisfaction from recommendations
                    if user_feedback:
                        total_feedbacks += len(user_feedback)
                        for ex_id, score in user_feedback.items():
                            feedback_data.append({'Exercise': ex_id, 'Score': score, 'User': uid})
                    else:
                        # Fallback: use simulated satisfaction from recommendations
                        for rec in recs:
                            ex_id = rec.get('exercise_id')
                            score = rec.get('simulated_satisfaction', 0)
                            if ex_id and score:
                                total_feedbacks += 1
                                feedback_data.append({'Exercise': ex_id, 'Score': score, 'User': uid})
            except:
                pass

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Recommendations", total_recommendations)
    with col2:
        st.metric("Total Feedback Scores", total_feedbacks)
    with col3:
        acceptance_rate = (total_feedbacks / total_recommendations * 100) if total_recommendations > 0 else 0
        st.metric("Engagement Rate", f"{acceptance_rate:.1f}%")

    # Always show feedback chart if there's any feedback data
    if feedback_data:
        st.markdown("---")
        st.write("**Exercise Satisfaction Scores** (from feedback & simulations)")

        feedback_df = pd.DataFrame(feedback_data)

        # Show average scores by exercise
        if not feedback_df.empty:
            avg_scores = feedback_df.groupby('Exercise')['Score'].mean().sort_values(ascending=False).head(10)
            st.bar_chart(avg_scores)

            # Show distribution of all feedback scores
            st.write("**Feedback Score Distribution**")
            col1, col2 = st.columns(2)
            with col1:
                score_counts = feedback_df['Score'].value_counts().sort_index()
                st.bar_chart(score_counts)
            with col2:
                st.write("**Summary Statistics**")
                st.metric("Average Score", f"{feedback_df['Score'].mean():.1f}/10")
                st.metric("Median Score", f"{feedback_df['Score'].median():.1f}/10")
                st.metric("Total Feedbacks", len(feedback_df))
    else:
        st.markdown("---")
        st.info("No feedback data available yet. Users need to provide feedback on recommendations.")


def analytics_ui(sys: RecommendationSystem):
    """Analytics dashboard with daily, weekly, and progress metrics"""
    st.header("Exercise Analytics Dashboard")
    
    analytics = ExerciseAnalytics("data", system=sys)
    profiles = list(sys.user_manager.profiles.keys())
    
    if not profiles:
        st.info("No users registered yet. Register a user first.")
        return
    
    # User selection
    user_id = st.selectbox("Select user for analytics", profiles, key="analytics_user")
    
    # Analytics sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Today's Summary", 
        "Weekly Progress", 
        "30-Day Trends", 
        "Time Patterns",
        "Recommendations", 
        "Comparison"
    ])
    
    # ===== Tab 1: Daily Summary =====
    with tab1:
        st.subheader("Today's Exercise Summary")
        
        daily = analytics.get_user_daily_summary(user_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Exercises", daily['total_exercises'])
        with col2:
            st.metric("Sessions", daily['total_sessions'])
        with col3:
            st.metric("Duration (min)", daily['total_duration_minutes'])
        with col4:
            st.metric("Calories Burned", int(daily['total_calories_burned']))
        
        st.markdown("---")
        
        # Time distribution
        if daily.get('time_distribution'):
            st.write("**📅 Time Distribution Today:**")
            time_dist = daily['time_distribution']
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🌅 Morning (6AM-12PM)", time_dist['morning'])
            with col2:
                st.metric("☀️ Afternoon (12PM-6PM)", time_dist['afternoon'])
            with col3:
                st.metric("🌆 Evening (6PM-12AM)", time_dist['evening'])
            with col4:
                st.metric("🌙 Night (12AM-6AM)", time_dist['night'])
        
        st.markdown("---")
        
        # Session details
        if daily.get('sessions'):
            st.write("**⏰ Session Details:**")
            for session in daily['sessions']:
                with st.expander(f"🕐 {session['time_of_day']} - {session['exercise_count']} exercises ({session['duration_minutes']} min)"):
                    session_df = pd.DataFrame([
                        {
                            'Exercise': ex['name'],
                            'Duration': f"{ex['duration']} min",
                            'Calories': round(ex['calories'], 1),
                            'Intensity': ex['intensity'],
                            'Satisfaction': f"{ex['satisfaction']:.1f}/10"
                        }
                        for ex in session['exercises']
                    ])
                    st.dataframe(session_df, use_container_width=True)
        
        # Overall exercises
        if daily['exercises']:
            st.write("**💪 All Exercises Today:**")
            exercise_df = pd.DataFrame([
                {
                    'Exercise': e['name'],
                    'Duration': f"{e['duration']} min",
                    'Calories': round(e['calories'], 1),
                    'Intensity': e['intensity'],
                    'Satisfaction': f"{e['satisfaction']:.1f}/10"
                }
                for e in daily['exercises']
            ])
            st.dataframe(exercise_df, use_container_width=True)
            
            # Muscle groups worked
            if daily['muscles_worked']:
                st.write("**🏋️ Muscles Worked:**")
                muscles_df = pd.DataFrame(
                    list(daily['muscles_worked'].items()),
                    columns=['Muscle Group', 'Frequency']
                )
                st.bar_chart(muscles_df.set_index('Muscle Group'))
        else:
            st.info("No exercises recorded for today yet")
    
    # ===== Tab 2: Weekly Progress =====
    with tab2:
        st.subheader("Last 7 Days Summary")
        
        weekly = analytics.get_weekly_summary(user_id, days_back=7)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Days Active", weekly['days_active'])
        with col2:
            st.metric("Activity Rate", f"{weekly['activity_rate']}%")
        with col3:
            st.metric("Total Exercises", weekly['total_exercises'])
        with col4:
            st.metric("Total Duration", f"{weekly['total_duration_minutes']:.0f} min")
        with col5:
            st.metric("Calories Burned", f"{int(weekly['total_calories_burned'])}")
        
        st.markdown("---")
        
        # Daily trend
        if weekly['daily_summaries']:
            daily_df = pd.DataFrame([
                {
                    'date': d['date'],
                    'exercises': d['total_exercises'],
                    'duration': d['total_duration_minutes'],
                    'calories': d['total_calories_burned'],
                    'satisfaction': d['average_satisfaction']
                }
                for d in weekly['daily_summaries']
            ])
            
            st.write("**Daily Trend:**")
            col1, col2 = st.columns(2)
            with col1:
                st.line_chart(daily_df.set_index('date')[['exercises', 'duration']])
            with col2:
                st.line_chart(daily_df.set_index('date')[['calories', 'satisfaction']])
        
        # Most frequent exercises
        if weekly['most_frequent_exercises']:
            st.write("**Most Frequent Exercises:**")
            freq_df = pd.DataFrame(
                weekly['most_frequent_exercises'],
                columns=['Exercise', 'Count']
            )
            st.bar_chart(freq_df.set_index('Exercise'))
    
    # ===== Tab 3: 30-Day Trends =====
    with tab3:
        st.subheader("30-Day Progress Metrics")
        
        progress = analytics.get_progress_metrics(user_id, days_back=30)
        
        if progress:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Sessions", progress['total_sessions'])
            with col2:
                st.metric("Session Frequency", f"{progress['session_frequency']}%")
            with col3:
                st.metric("Avg Duration", f"{progress['average_session_duration']:.0f} min")
            with col4:
                st.metric("Avg Intensity", f"{progress['average_session_intensity']:.1f}/10")
            with col5:
                st.metric("Avg Satisfaction", f"{progress['average_satisfaction']:.1f}/10")
            
            st.markdown("---")
            
            # Streaks
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Current Streak", f"{progress['streak_current']} days")
            with col2:
                st.metric("Longest Streak", f"{progress['streak_longest']} days")
            
            st.markdown("---")
            
            # Trends
            st.write("**Trends (30 days):**")
            trend_map = {'positive': 'Improving 📈', 'negative': 'Declining 📉', 'stable': 'Stable →'}
            trend_data = {
                'Duration': trend_map.get(progress['duration_trend'], 'Unknown'),
                'Intensity': trend_map.get(progress['intensity_trend'], 'Unknown'),
                'Satisfaction': trend_map.get(progress['satisfaction_trend'], 'Unknown')
            }
            trend_df = pd.DataFrame(list(trend_data.items()), columns=['Metric', 'Trend'])
            st.dataframe(trend_df, use_container_width=True)
        else:
            st.info("No data available for analysis")
    
    # ===== Tab 4: Time Patterns =====
    with tab4:
        st.subheader("⏰ Exercise Time Patterns (30 Days)")
        
        time_analysis = analytics.get_time_analysis(user_id, days_back=30)
        
        if time_analysis:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Sessions", time_analysis['total_sessions_analyzed'])
            with col2:
                st.metric("Peak Hour", time_analysis['peak_hour'])
            with col3:
                st.metric("Peak Sessions", time_analysis['peak_hour_sessions'])
            with col4:
                most_active = time_analysis.get('most_active_day', 'N/A')
                st.metric("Most Active Day", most_active)
            
            st.markdown("---")
            
            # Time of day distribution
            st.write("**🕐 Time of Day Distribution:**")
            time_dist = time_analysis['time_distribution']
            
            # Create pie chart data
            time_labels = ['Morning (6AM-12PM)', 'Afternoon (12PM-6PM)', 'Evening (6PM-12AM)', 'Night (12AM-6AM)']
            time_values = [time_dist['morning'], time_dist['afternoon'], time_dist['evening'], time_dist['night']]
            
            if sum(time_values) > 0:
                fig, ax = plt.subplots()
                ax.pie(time_values, labels=time_labels, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
            
            # Hourly breakdown
            st.write("**📊 Hourly Activity Pattern:**")
            hourly_data = time_analysis['hourly_breakdown']
            
            # Create 24-hour chart
            hours = list(range(24))
            hour_labels = [f"{h:02d}:00" for h in hours]
            hour_values = [hourly_data.get(h, 0) for h in hours]
            
            hour_df = pd.DataFrame({
                'Hour': hour_labels,
                'Sessions': hour_values
            })
            st.bar_chart(hour_df.set_index('Hour'))
            
            # Weekly patterns
            st.write("**📅 Weekly Patterns:**")
            weekly_patterns = time_analysis['weekly_patterns']
            
            # Create heatmap-style visualization
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = []
            
            for day in days_order:
                day_data = weekly_patterns.get(day, {})
                row = [day_data.get(h, 0) for h in range(24)]
                heatmap_data.append(row)
            
            if heatmap_data:
                fig, ax = plt.subplots(figsize=(12, 6))
                im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
                
                # Set labels
                ax.set_xticks(range(24))
                ax.set_xticklabels([f"{h:02d}" for h in range(24)])
                ax.set_yticks(range(7))
                ax.set_yticklabels(days_order)
                
                plt.colorbar(im, ax=ax, label='Sessions')
                ax.set_title('Exercise Sessions by Day and Hour')
                st.pyplot(fig)
        else:
            st.info("No time pattern data available yet")
    
    # ===== Tab 5: Recommendation Analysis =====
    with tab5:
        st.subheader("Recommendation Effectiveness")
        
        rec_analysis = analytics.get_exercise_recommendations_analysis(user_id)
        
        if rec_analysis:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Recommendations", rec_analysis['total_recommendations'])
            with col2:
                st.metric("Completions", rec_analysis['total_completions'])
            with col3:
                st.metric("Acceptance Rate", f"{rec_analysis['acceptance_rate']:.1f}%")
            with col4:
                st.metric("Avg Satisfaction", f"{rec_analysis['average_satisfaction']:.1f}/10")
            
            st.markdown("---")
            
            # Top rated exercises
            if rec_analysis['top_rated_exercises']:
                st.write("**Top Rated Exercises:**")
                top_df = pd.DataFrame(
                    rec_analysis['top_rated_exercises'],
                    columns=['Exercise ID', 'Avg Rating']
                )
                st.bar_chart(top_df.set_index('Exercise ID'))
        else:
            st.info("No recommendation data available yet")
        
        # Injury impact
        injury_analysis = analytics.get_injury_impact_analysis(user_id)
        if injury_analysis.get('injuries'):
            st.markdown("---")
            st.write("**Health Constraints:**")
            st.write(f"Injuries/Constraints: {', '.join(injury_analysis['injuries'])}")
            st.write(f"Safe Exercises Completed: {injury_analysis['safe_exercise_count']}")
    
    # ===== Tab 6: User Comparison =====
    with tab6:
        st.subheader("Compare Users")
        
        compare_users = st.multiselect(
            "Select users to compare",
            profiles,
            default=[profiles[0]] if profiles else [],
            key="compare_users_select"
        )
        
        if compare_users and len(compare_users) > 1:
            comparison = analytics.get_comparison_metrics(compare_users, days_back=7)
            
            if comparison.get('user_metrics'):
                # Comparison table
                comparison_data = []
                for uid, metrics in comparison['user_metrics'].items():
                    comparison_data.append({
                        'User': uid,
                        'Activity Rate (%)': metrics['activity_rate'],
                        'Total Exercises': metrics['total_exercises'],
                        'Duration (min)': metrics['total_duration'],
                        'Days Active': metrics['days_active']
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, use_container_width=True)
                
                # Rankings
                st.markdown("---")
                st.write("**Rankings (Last 7 days):**")
                
                col1, col2, col3 = st.columns(3)
                
                if comparison['rankings']['most_active']:
                    with col1:
                        st.metric("Most Active", comparison['rankings']['most_active'][0])
                
                if comparison['rankings']['most_exercises']:
                    with col2:
                        st.metric("Most Exercises", comparison['rankings']['most_exercises'][0])
                
                if comparison['rankings']['longest_duration']:
                    with col3:
                        st.metric("Longest Duration", comparison['rankings']['longest_duration'][0])
        elif len(compare_users) == 1:
            st.info("Select at least 2 users to compare")
        else:
            st.info("Select users to compare")


def main():
    st.title("Exercise Recommendation Dashboard")
    st.sidebar.title("Controls")

    sys = get_system()

    st.sidebar.markdown("### Actions")
    view = st.sidebar.selectbox("View", ["Recommendations", "Register User", "Exercises", "Metrics", "Analytics", "Admin"], index=0)

    if view == "Register User":
        user_registration_ui(sys)
    elif view == "Recommendations":
        recommendations_ui(sys)
    elif view == "Exercises":
        exercises_ui(sys)
    elif view == "Metrics":
        metrics_ui(sys)
    elif view == "Analytics":
        analytics_ui(sys)
    elif view == "Admin":
        admin_ui(sys)


if __name__ == '__main__':
    main()
