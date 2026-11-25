"""
Exercise Recommendation System
Main interface for generating personalized exercise recommendations,
tracking completions, computing safety adjustments, and persisting history.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
import torch

from user_profile import UserProfile, UserProfileManager, FitnessLevel
from exercise_database import ExerciseDatabase, Exercise
from rl_agent import DQNAgent, PolicyGradientAgent


class ExerciseRecommender:
    """Main recommender system using a trained RL agent and safety heuristics."""

    def __init__(
        self,
        agent: DQNAgent,
        exercise_db: ExerciseDatabase,
        user_id: str,
        user_profile: UserProfile,
        data_dir: str = "data"
    ):
        """
        Initialize recommender for a specific user.

        Args:
            agent: Trained RL agent
            exercise_db: Exercise database
            user_id: ID of user
            user_profile: User's fitness profile
            data_dir: Directory path for persisting user history
        """
        self.agent = agent
        self.exercise_db = exercise_db
        self.user_id = user_id
        self.user_profile = user_profile
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Include exercises at or below the user's fitness level so variety isn't overly restricted
        all_exs = exercise_db.get_all_exercises()
        self.suitable_exercises = [
            ex for ex in all_exs
            if ex.is_suitable_for(user_profile.injuries)
            and ex.requires_equipment(user_profile.equipment_access)
            and ex.difficulty.value <= user_profile.fitness_level.value
        ]

        # Fallback: if strict filtering yields fewer than 4 exercises, relax difficulty constraint
        if len(self.suitable_exercises) < 4:
            self.suitable_exercises = [
                ex for ex in all_exs
                if ex.is_suitable_for(user_profile.injuries)
                and ex.requires_equipment(user_profile.equipment_access)
            ]

        # Tracking
        self.recommendation_history: List[Dict[str, Any]] = []
        self.user_feedback: Dict[str, float] = {}

        # Load any persisted history for this user
        try:
            self._load_persistence()
        except Exception:
            pass

    def _format_recommendation(self, exercise: Exercise, rank: int, repeat: bool = False) -> Dict[str, Any]:
        """Format an Exercise object into a standardized recommendation dictionary."""
        rationale = self._generate_rationale(exercise)
        if repeat:
            rationale += " (repeat)"
        safety = self.get_safety_info(exercise.exercise_id)

        return {
            'rank': rank,
            'exercise_id': exercise.exercise_id,
            'exercise_name': exercise.name,
            'description': exercise.description,
            'duration_minutes': exercise.duration_minutes,
            'intensity_level': exercise.intensity_level,
            'calories_burned': exercise.calories_burned,
            'sets': exercise.sets,
            'reps': exercise.reps,
            'primary_muscles': [m.value for m in exercise.primary_muscles],
            'equipment_required': exercise.equipment_required,
            'rationale': rationale,
            'total_calories': round(exercise.duration_minutes * exercise.calories_burned, 1),
            'safety_info': safety
        }

    def get_recommendations(
        self,
        num_recommendations: int = 5,
        use_exploration: bool = False,
        available_time_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top exercise recommendations for the user.

        Args:
            num_recommendations: Number of recommendations to return (ignored if available_time_minutes is set)
            use_exploration: If True, include randomness for exploration
            available_time_minutes: If set, build a workout fitting this time duration

        Returns:
            List of recommended exercises with details
        """
        if not self.suitable_exercises:
            return []

        if available_time_minutes is not None:
            return self._build_timed_workout(available_time_minutes, use_exploration)

        num_recommendations = max(1, int(num_recommendations))

        if use_exploration and np.random.random() < 0.15:
            action_indices = np.random.choice(
                len(self.suitable_exercises),
                size=min(num_recommendations, len(self.suitable_exercises)),
                replace=False
            )
        else:
            action_indices = self._get_best_actions(num_recommendations)

        recommendations = []
        for idx, action in enumerate(action_indices):
            exercise = self.suitable_exercises[action]
            recommendations.append(self._format_recommendation(exercise, rank=idx + 1))

        # Cycle through suitable exercises if user explicitly requested more than available unique ones
        if len(recommendations) < num_recommendations and self.suitable_exercises:
            i = 0
            while len(recommendations) < num_recommendations:
                ex = self.suitable_exercises[i % len(self.suitable_exercises)]
                recommendations.append(
                    self._format_recommendation(ex, rank=len(recommendations) + 1, repeat=True)
                )
                i += 1

        # Record standardized recommendation history for analytics
        self._log_recommendations_to_history(recommendations)
        return recommendations

    def _log_recommendations_to_history(self, recommendations: List[Dict[str, Any]]):
        """Record generated recommendations distinctly from completed workouts."""
        try:
            from exercise_env import ExerciseRecommendationEnv
            timestamp = datetime.utcnow().isoformat()

            try:
                temp_env = ExerciseRecommendationEnv(self.user_profile, self.exercise_db)
            except Exception:
                temp_env = None

            for rec in recommendations:
                sim_score = None
                sim_reward = None
                try:
                    if temp_env is not None:
                        ex = self.exercise_db.get_exercise(rec['exercise_id'])
                        sim_score = float(temp_env._simulate_user_feedback(ex))
                        sim_reward = float(temp_env._calculate_reward(ex, sim_score))
                except Exception:
                    pass

                entry = {
                    'timestamp': timestamp,
                    'event_type': 'recommended',
                    'exercise_id': rec['exercise_id'],
                    'exercise_name': rec['exercise_name'],
                    'duration_minutes': rec['duration_minutes'],
                    'intensity_level': rec['intensity_level'],
                    'calories_burned': rec['calories_burned'],
                    'total_calories': rec.get('total_calories', 0),
                    'completed': False,
                    'simulated_satisfaction': sim_score,
                    'simulated_reward': sim_reward
                }
                self.recommendation_history.append(entry)

            self._save_persistence()
        except Exception:
            pass

    def recommend_personalized_workout(self, session_duration: int = 45) -> Dict[str, Any]:
        """
        Generate a structured personalized workout plan fitting session_duration.
        """
        selected_exercises = self._build_timed_workout(session_duration, use_exploration=False)
        total_duration = sum(ex['duration_minutes'] for ex in selected_exercises)
        estimated_calories = sum(ex['total_calories'] for ex in selected_exercises)

        return {
            'user_id': self.user_id,
            'requested_duration': session_duration,
            'total_duration': total_duration,
            'exercises': selected_exercises,
            'estimated_calories': round(estimated_calories, 1),
            'difficulty': self.user_profile.fitness_level.name,
            'goals_targeted': [goal.value for goal in self.user_profile.goals]
        }

    def provide_feedback(self, exercise_id: str, satisfaction_score: float):
        """
        Record user feedback on an exercise.

        Args:
            exercise_id: ID of exercise
            satisfaction_score: User satisfaction (0-10)
        """
        if not 0 <= satisfaction_score <= 10:
            raise ValueError("Satisfaction score must be between 0 and 10")

        self.user_feedback[exercise_id] = float(satisfaction_score)
        self._save_persistence()

    def record_completion(self, exercise_id: str, satisfaction_score: Optional[float] = None) -> Dict[str, Any]:
        """
        Record that the user completed an exercise, compute RL reward,
        and persist the completion entry.
        """
        from exercise_env import ExerciseRecommendationEnv

        ex = self.exercise_db.get_exercise(exercise_id)
        if ex is None:
            raise ValueError(f"Exercise '{exercise_id}' not found")

        try:
            temp_env = ExerciseRecommendationEnv(self.user_profile, self.exercise_db)
        except Exception:
            temp_env = None

        if satisfaction_score is None:
            sim_satisfaction = float(temp_env._simulate_user_feedback(ex)) if temp_env is not None else 7.0
        else:
            if not 0 <= satisfaction_score <= 10:
                raise ValueError("Satisfaction score must be between 0 and 10")
            sim_satisfaction = float(satisfaction_score)

        sim_reward = None
        if temp_env is not None:
            try:
                sim_reward = float(temp_env._calculate_reward(ex, sim_satisfaction))
            except Exception:
                sim_reward = 0.0

        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'completed',
            'exercise_id': exercise_id,
            'exercise_name': ex.name,
            'duration_minutes': ex.duration_minutes,
            'intensity_level': ex.intensity_level,
            'calories_burned': ex.calories_burned,
            'total_calories': round(ex.duration_minutes * ex.calories_burned, 1),
            'completed': True,
            'satisfaction': round(sim_satisfaction, 2),
            'simulated_satisfaction': round(sim_satisfaction, 2),
            'reward': round(sim_reward, 3) if sim_reward is not None else None
        }

        self.recommendation_history.append(entry)
        self.user_feedback[exercise_id] = round(sim_satisfaction, 2)
        self._save_persistence()

        return entry

    def get_recommendation_history(self) -> List[Dict[str, Any]]:
        """Get a copy of the user's recommendation and completion history."""
        return self.recommendation_history.copy()

    # ---------------------------- Persistence ----------------------------
    def _history_file_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / f"{self.user_id}_history.json"

    def _load_persistence(self):
        path = self._history_file_path()
        if not path.exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        self.recommendation_history = payload.get('recommendation_history', [])
        self.user_feedback = payload.get('user_feedback', {})

    def _save_persistence(self):
        path = self._history_file_path()
        tmp = path.with_suffix('.tmp')
        payload = {
            'user_id': self.user_id,
            'updated_at': datetime.utcnow().isoformat(),
            'recommendation_history': self.recommendation_history,
            'user_feedback': self.user_feedback
        }
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)

    def _get_user_state(self) -> np.ndarray:
        """Build 15-dimensional state vector matching trained DQN input dimensions."""
        state = np.zeros(15, dtype=np.float32)

        # User profile features
        state[0] = self.user_profile.age / 100.0
        state[1] = self.user_profile.fitness_level.value / 3.0
        state[2] = self.user_profile.available_time / 120.0
        state[3] = len(self.user_profile.goals) / 5.0

        # Biometric / daily condition features
        state[4] = getattr(self.user_profile, 'fatigue', 0.0) / 10.0
        state[5] = getattr(self.user_profile, 'soreness', 0.0) / 10.0
        state[6] = getattr(self.user_profile, 'sleep_hours', 8.0) / 12.0
        state[7] = getattr(self.user_profile, 'resting_heart_rate', 60) / 150.0
        state[8] = len(self.user_profile.injuries) / 5.0

        # Recent feedback scores
        if self.user_feedback:
            feedback_scores = list(self.user_feedback.values())[-6:]
            for i, score in enumerate(feedback_scores):
                state[9 + i] = score / 10.0

        return state

    def _get_best_actions(self, num_actions: int) -> List[int]:
        """Rank suitable exercises using DQN Q-values combined with user profile alignment."""
        if not self.suitable_exercises:
            return []

        state = self._get_user_state()
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.agent.device)
        with torch.no_grad():
            q_values = self.agent.q_network(state_tensor).squeeze(0).cpu().numpy()

        all_exercises = self.exercise_db.get_all_exercises()
        id_to_global_idx = {ex.exercise_id: i for i, ex in enumerate(all_exercises)}

        scored_indices = []
        for local_idx, exercise in enumerate(self.suitable_exercises):
            global_idx = id_to_global_idx.get(exercise.exercise_id, local_idx)
            raw_q = float(q_values[global_idx]) if global_idx < len(q_values) else 0.0
            total_score = self._score_exercise_alignment(exercise, raw_q)
            scored_indices.append((total_score, local_idx))

        scored_indices.sort(key=lambda pair: pair[0], reverse=True)
        return [idx for _, idx in scored_indices[:num_actions]]

    def _build_timed_workout(self, available_time_minutes: int, use_exploration: bool = False) -> List[Dict[str, Any]]:
        """Build a balanced, goal-aligned workout session that fits within available_time_minutes."""
        recommendations = []
        remaining_time = max(5, int(available_time_minutes))

        if use_exploration and np.random.random() < 0.15:
            best_actions = np.random.permutation(len(self.suitable_exercises))
        else:
            best_actions = self._get_best_actions(len(self.suitable_exercises))

        selected_muscles = set()
        deferred_indices = []
        rank = 1

        # First pass: prioritize muscle variety while respecting remaining time
        for action_idx in best_actions:
            if remaining_time <= 0:
                break
            exercise = self.suitable_exercises[action_idx]
            if exercise.duration_minutes <= remaining_time:
                ex_muscles = {m.value for m in exercise.primary_muscles}
                if selected_muscles and ex_muscles.issubset(selected_muscles) and len(deferred_indices) < 6:
                    deferred_indices.append(action_idx)
                    continue
                recommendations.append(self._format_recommendation(exercise, rank=rank))
                remaining_time -= exercise.duration_minutes
                selected_muscles.update(ex_muscles)
                rank += 1

        # Second pass: fill remaining time budget with deferred exercises
        for action_idx in deferred_indices:
            if remaining_time <= 0:
                break
            exercise = self.suitable_exercises[action_idx]
            if exercise.duration_minutes <= remaining_time:
                recommendations.append(self._format_recommendation(exercise, rank=rank))
                remaining_time -= exercise.duration_minutes
                rank += 1

        # Third pass: if user has a long session budget (e.g., 60-120 min), add finisher/accessory rounds
        if remaining_time >= 5 and self.suitable_exercises:
            sorted_by_score = [self.suitable_exercises[i] for i in best_actions]
            already_ids = {r['exercise_id'] for r in recommendations}
            for exercise in sorted_by_score:
                if remaining_time <= 0:
                    break
                if exercise.duration_minutes <= remaining_time:
                    is_repeat = exercise.exercise_id in already_ids
                    recommendations.append(self._format_recommendation(exercise, rank=rank, repeat=is_repeat))
                    already_ids.add(exercise.exercise_id)
                    remaining_time -= exercise.duration_minutes
                    rank += 1

        self._log_recommendations_to_history(recommendations)
        return recommendations

    def _score_exercise_alignment(self, exercise: Exercise, raw_q: float) -> float:
        """Combine normalized DQN Q-value with goal, equipment, preference, feedback, and recovery alignment."""
        score = float(np.tanh(raw_q)) * 1.5

        # 1. Strong Goal Alignment Boost
        goal_values = {g.value for g in self.user_profile.goals}
        muscles = {m.value for m in exercise.primary_muscles}
        ex_id = exercise.exercise_id.lower()

        if "weight_loss" in goal_values:
            score += (exercise.calories_burned / 10.0) * 3.5 + (exercise.intensity_level / 10.0) * 2.0
            if "cardio" in muscles or "full_body" in muscles:
                score += 2.0
        if "muscle_gain" in goal_values:
            if muscles.intersection({"chest", "back", "biceps", "triceps", "shoulders", "quadriceps", "glutes", "hamstrings"}):
                score += 3.5
            if exercise.equipment_required:
                score += 1.2
        if "endurance" in goal_values:
            if "cardio" in muscles or exercise.duration_minutes >= 15:
                score += 3.5
        if "flexibility" in goal_values:
            if exercise.intensity_level <= 4 or ex_id in {"yoga", "stretching", "dynamic_stretching", "foam_rolling"}:
                score += 4.5
        if "general_fitness" in goal_values:
            score += 1.5

        # 2. Equipment Utilization Bonus (prioritize exercises using user's selected equipment)
        user_eq = {e.lower() for e in self.user_profile.equipment_access}
        if user_eq and exercise.equipment_required:
            if set(e.lower() for e in exercise.equipment_required).issubset(user_eq):
                score += 1.8

        # 3. User Preference Boost
        prefs_lower = [p.strip().lower() for p in self.user_profile.preferred_exercises]
        if ex_id in prefs_lower or exercise.name.lower() in prefs_lower:
            score += 3.0

        # 4. Historical Satisfaction Feedback Adjustment
        if exercise.exercise_id in self.user_feedback:
            fb = self.user_feedback[exercise.exercise_id]
            score += (fb - 5.0) * 0.6

        # 5. Biometric Recovery Penalty for Overly Intense Exercises
        fatigue = getattr(self.user_profile, 'fatigue', 0.0)
        soreness = getattr(self.user_profile, 'soreness', 0.0)
        if (fatigue >= 6.0 or soreness >= 6.0) and exercise.intensity_level >= 7:
            score -= 4.0

        return score

    def _generate_rationale(self, exercise: Exercise) -> str:
        """Generate clear, user-specific explanation for why an exercise was recommended."""
        reasons = []
        goal_values = {g.value for g in self.user_profile.goals}
        muscles = [m.value.replace('_', ' ') for m in exercise.primary_muscles]

        if "weight_loss" in goal_values and exercise.calories_burned >= 8:
            reasons.append(f"high calorie burn (~{exercise.calories_burned} kcal/min) for fat loss")
        if "muscle_gain" in goal_values and any(m in {"chest", "back", "shoulders", "biceps", "triceps", "quadriceps", "glutes", "hamstrings"} for m in muscles):
            reasons.append(f"builds {', '.join(muscles)} strength")
        if "endurance" in goal_values and ("cardio" in muscles or exercise.duration_minutes >= 15):
            reasons.append("improves cardiovascular stamina")
        if "flexibility" in goal_values and exercise.intensity_level <= 4:
            reasons.append("enhances mobility & recovery")

        if exercise.equipment_required:
            reasons.append(f"uses your {', '.join(exercise.equipment_required)}")
        else:
            reasons.append("bodyweight-friendly")

        if not reasons:
            reasons.append(f"targets {', '.join(muscles)} at {exercise.difficulty.name.lower()} level")

        return "Matches your profile: " + "; ".join(reasons) + "."

    def get_safety_info(self, exercise_id: str) -> Dict[str, Any]:
        """Compute personalized safety guidance and intensity/duration adjustments."""
        ex = self.exercise_db.get_exercise(exercise_id)
        if ex is None:
            return {
                'best_exercise_type': 'general',
                'recommended_intensity': 5,
                'safe_duration': 15.0,
                'unsafe': False,
                'notes': 'Standard safety precautions apply'
            }

        pg = [m.value for m in ex.primary_muscles]
        if 'cardio' in pg:
            best_type = 'cardio'
        elif any(m in pg for m in ['chest', 'back', 'shoulders', 'biceps', 'triceps', 'quadriceps', 'glutes', 'hamstrings']):
            best_type = 'strength'
        elif 'abs' in pg or 'core' in pg:
            best_type = 'core'
        else:
            best_type = 'flexibility' if ex.intensity_level <= 3 else 'general'

        base_int = ex.intensity_level
        fatigue = getattr(self.user_profile, 'fatigue', 0.0)
        soreness = getattr(self.user_profile, 'soreness', 0.0)
        sleep_hours = getattr(self.user_profile, 'sleep_hours', 8.0)
        resting_hr = getattr(self.user_profile, 'resting_heart_rate', 60)
        age = getattr(self.user_profile, 'age', 30)

        intensity_penalty = int(round((fatigue + soreness) / 5.0))
        rec_intensity = max(1, base_int - intensity_penalty)

        if resting_hr and resting_hr >= 100:
            rec_intensity = max(1, rec_intensity - 2)

        if age >= 65:
            rec_intensity = min(rec_intensity, 5)

        safe_dur = float(ex.duration_minutes)
        if fatigue >= 8 or soreness >= 8:
            safe_dur = max(5.0, safe_dur * 0.5)
        if sleep_hours < 5:
            safe_dur = max(5.0, safe_dur * 0.7)
        if age >= 65 and ex.intensity_level >= 7:
            safe_dur = max(5.0, safe_dur * 0.7)

        unsafe = False
        notes = []

        for inj in self.user_profile.injuries:
            if inj in ex.contraindications:
                unsafe = True
                notes.append(f"Contraindicated for {inj.replace('_', ' ')}")

        if base_int >= 8 and (fatigue >= 6 or soreness >= 6):
            unsafe = True
            notes.append("High intensity not recommended while fatigued or sore")

        if resting_hr >= 110 and base_int >= 7:
            unsafe = True
            notes.append("Elevated resting heart rate — reduce intensity")

        if not notes:
            if rec_intensity < base_int or safe_dur < ex.duration_minutes:
                notes = [f"Adjusted for recovery (Fatigue: {fatigue}/10, Soreness: {soreness}/10)"]
            else:
                notes = ["Safe to perform at full prescribed intensity"]

        return {
            'best_exercise_type': best_type,
            'recommended_intensity': int(rec_intensity),
            'safe_duration': float(round(safe_dur, 1)),
            'unsafe': unsafe,
            'notes': "; ".join(notes)
        }


class RecommendationSystem:
    """Complete recommendation system with user management and persistent profiles."""

    def __init__(self, agent_path: Optional[str] = None, data_dir: str = "data"):
        """
        Initialize recommendation system.

        Args:
            agent_path: Path to trained PyTorch agent checkpoint
            data_dir: Directory where user profiles and histories are stored
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_file = self.data_dir / "user_profiles.json"

        self.exercise_db = ExerciseDatabase()
        self.user_manager = UserProfileManager()

        total_exercises = len(self.exercise_db.get_all_exercises())
        self.agent = DQNAgent(state_size=15, action_size=total_exercises)
        if agent_path and os.path.exists(agent_path):
            try:
                self.agent.load(agent_path)
            except Exception as e:
                print(f"Warning: Could not load agent weights from {agent_path}: {e}")

        self.recommenders: Dict[str, ExerciseRecommender] = {}
        self._load_saved_profiles()

    def _save_profiles(self):
        """Persist registered user profiles so users survive server/dashboard restarts."""
        try:
            serialized = {}
            for uid, p in self.user_manager.profiles.items():
                serialized[uid] = {
                    'user_id': p.user_id,
                    'age': p.age,
                    'fitness_level': p.fitness_level.name,
                    'goals': [g.value for g in p.goals],
                    'available_time': p.available_time,
                    'injuries': p.injuries,
                    'equipment_access': p.equipment_access,
                    'preferred_exercises': p.preferred_exercises,
                    'fatigue': getattr(p, 'fatigue', 0.0),
                    'soreness': getattr(p, 'soreness', 0.0),
                    'sleep_hours': getattr(p, 'sleep_hours', 8.0),
                    'resting_heart_rate': getattr(p, 'resting_heart_rate', 60)
                }
            tmp = self.profiles_file.with_suffix('.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(serialized, f, indent=2)
            os.replace(tmp, self.profiles_file)
        except Exception:
            pass

    def _load_saved_profiles(self):
        """Restore previously registered user profiles from disk on startup."""
        from user_profile import UserGoal
        if not self.profiles_file.exists():
            return
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                serialized = json.load(f)
            for uid, data in serialized.items():
                goals = []
                for g in data.get('goals', []):
                    try:
                        goals.append(UserGoal(g))
                    except ValueError:
                        pass
                profile = UserProfile(
                    user_id=data['user_id'],
                    age=int(data.get('age', 30)),
                    fitness_level=FitnessLevel[data.get('fitness_level', 'BEGINNER')],
                    goals=goals or [UserGoal.GENERAL_FITNESS],
                    available_time=int(data.get('available_time', 30)),
                    injuries=data.get('injuries', []),
                    equipment_access=data.get('equipment_access', []),
                    preferred_exercises=data.get('preferred_exercises', []),
                    fatigue=float(data.get('fatigue', 0.0)),
                    soreness=float(data.get('soreness', 0.0)),
                    sleep_hours=float(data.get('sleep_hours', 8.0)),
                    resting_heart_rate=int(data.get('resting_heart_rate', 60))
                )
                self.user_manager.profiles[uid] = profile
                self.recommenders[uid] = ExerciseRecommender(
                    agent=self.agent,
                    exercise_db=self.exercise_db,
                    user_id=uid,
                    user_profile=profile,
                    data_dir=str(self.data_dir)
                )
        except Exception:
            pass

    def register_user(self, user_profile: UserProfile) -> ExerciseRecommender:
        """Register or update a user and create their recommender."""
        self.user_manager.profiles[user_profile.user_id] = user_profile

        recommender = ExerciseRecommender(
            agent=self.agent,
            exercise_db=self.exercise_db,
            user_id=user_profile.user_id,
            user_profile=user_profile,
            data_dir=str(self.data_dir)
        )

        self.recommenders[user_profile.user_id] = recommender
        self._save_profiles()
        return recommender

    def get_recommender(self, user_id: str) -> ExerciseRecommender:
        """Get recommender for a registered user."""
        if user_id not in self.recommenders:
            raise ValueError(f"User '{user_id}' not registered")
        return self.recommenders[user_id]

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user's profile."""
        if user_id not in self.user_manager.profiles:
            raise ValueError(f"User '{user_id}' not found")
        return self.user_manager.profiles[user_id]