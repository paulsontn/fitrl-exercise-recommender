"""
Exercise Recommendation System
Main interface for generating personalized exercise recommendations
"""

import numpy as np
from typing import List, Dict, Any
from user_profile import UserProfile, UserProfileManager, FitnessLevel
from exercise_database import ExerciseDatabase, Exercise
from rl_agent import DQNAgent, PolicyGradientAgent
import os
import json
from pathlib import Path


class ExerciseRecommender:
    """Main recommender system using trained RL agent"""
    
    def __init__(self, agent: DQNAgent, exercise_db: ExerciseDatabase,
                 user_id: str, user_profile: UserProfile):
        """
        Initialize recommender
        
        Args:
            agent: Trained RL agent
            exercise_db: Exercise database
            user_id: ID of user
            user_profile: User's fitness profile
        """
        self.agent = agent
        self.exercise_db = exercise_db
        self.user_id = user_id
        self.user_profile = user_profile
        
        # Get suitable exercises
        self.suitable_exercises = exercise_db.get_suitable_exercises(
            injuries=user_profile.injuries,
            available_equipment=user_profile.equipment_access,
            difficulty=user_profile.fitness_level
        )
        
        # Tracking
        self.recommendation_history: List[Dict] = []
        self.user_feedback: Dict[str, float] = {}
        # Try to load any persisted history for this user
        try:
            self._load_persistence()
        except Exception:
            pass
    
    def get_recommendations(self, num_recommendations: int = 5,
                           use_exploration: bool = False,
                           available_time_minutes: int = None) -> List[Dict[str, Any]]:
        """
        Get top exercise recommendations for the user
        
        Args:
            num_recommendations: Number of recommendations to return (ignored if available_time_minutes is set)
            use_exploration: If True, include some randomness for exploration
            available_time_minutes: If set, build a workout fitting this time duration
            
        Returns:
            List of recommended exercises with details that fit available time
        """
        recommendations = []
        
        # If available_time_minutes is set, build a session that fits the time
        if available_time_minutes is not None:
            return self._build_timed_workout(available_time_minutes, use_exploration)
        
        # Otherwise, get top N recommendations as before
        # Get Q-values for all actions
        state_tensor = self._get_user_state()
        
        if use_exploration:
            # Epsilon-greedy selection
            if np.random.random() < 0.1:  # 10% exploration
                action_indices = np.random.choice(
                    len(self.suitable_exercises),
                    size=min(num_recommendations, len(self.suitable_exercises)),
                    replace=False
                )
            else:
                action_indices = self._get_best_actions(num_recommendations)
        else:
            action_indices = self._get_best_actions(num_recommendations)
        
        for idx, action in enumerate(action_indices):
            exercise = self.suitable_exercises[action]
            rec = {
                'rank': idx + 1,
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
                'rationale': self._generate_rationale(exercise),
                'total_calories': exercise.duration_minutes * exercise.calories_burned
            }
            recommendations.append(rec)

        # Record recommendation history for analytics, including estimated reward
        try:
            from datetime import datetime
            from exercise_env import ExerciseRecommendationEnv

            timestamp = datetime.utcnow().isoformat()
            # Create a temporary env to compute simulated feedback + reward per exercise
            try:
                temp_env = ExerciseRecommendationEnv(self.user_profile, self.exercise_db)
            except Exception:
                temp_env = None

            for rec in recommendations:
                entry = {
                    'timestamp': timestamp,
                    'exercise_id': rec['exercise_id'],
                    'exercise_name': rec['exercise_name']
                }
                # If possible, compute simulated feedback and reward
                try:
                    if temp_env is not None:
                        # find exercise object
                        ex = self.exercise_db.get_exercise(rec['exercise_id'])
                        sim_score = temp_env._simulate_user_feedback(ex)
                        sim_reward = temp_env._calculate_reward(ex, sim_score)
                        entry['simulated_satisfaction'] = float(sim_score)
                        entry['simulated_reward'] = float(sim_reward)
                except Exception:
                    entry['simulated_satisfaction'] = None
                    entry['simulated_reward'] = None

                self.recommendation_history.append(entry)
            # persist after adding entries
            try:
                self._save_persistence()
            except Exception:
                pass
        except Exception:
            # Non-critical: don't break recommendations if history logging fails
            pass

        # If fewer recommendations were returned than requested, fill by cycling
        try:
            if len(recommendations) < num_recommendations and self.suitable_exercises:
                # cycle through suitable_exercises to fill up to num_recommendations
                i = 0
                while len(recommendations) < num_recommendations:
                    ex = self.suitable_exercises[i % len(self.suitable_exercises)]
                    # avoid duplicating exact same recommendation object for ranking clarity
                    rec = {
                        'rank': len(recommendations) + 1,
                        'exercise_id': ex.exercise_id,
                        'exercise_name': ex.name,
                        'description': ex.description,
                        'duration_minutes': ex.duration_minutes,
                        'intensity_level': ex.intensity_level,
                        'calories_burned': ex.calories_burned,
                        'sets': ex.sets,
                        'reps': ex.reps,
                        'primary_muscles': [m.value for m in ex.primary_muscles],
                        'equipment_required': ex.equipment_required,
                        'rationale': self._generate_rationale(ex) + ' (repeat)',
                        'total_calories': ex.duration_minutes * ex.calories_burned
                    }
                    recommendations.append(rec)
                    i += 1
        except Exception:
            pass
        # persist after generating recommendations (in case entries were added)
        try:
            self._save_persistence()
        except Exception:
            pass

        return recommendations
    
    def recommend_personalized_workout(self, session_duration: int = 45) -> Dict[str, Any]:
        """
        Generate a personalized workout plan
        
        Args:
            session_duration: Total session duration in minutes
            
        Returns:
            Personalized workout plan
        """
        recommendations = self.get_recommendations(num_recommendations=30)
        
        # Select exercises to fit session duration
        selected_exercises = []
        remaining_time = session_duration
        
        for rec in recommendations:
            exercise = self.exercise_db.get_exercise(rec['exercise_id'])
            if exercise.duration_minutes <= remaining_time:
                selected_exercises.append(rec)
                remaining_time -= exercise.duration_minutes
        
        # If no exercises fit, select the first few that partially fit
        if not selected_exercises and recommendations:
            selected_exercises = recommendations[:3]
        
        return {
            'user_id': self.user_id,
            'total_duration': session_duration,
            'exercises': selected_exercises,
            'estimated_calories': sum(
                self.exercise_db.get_exercise(ex['exercise_id']).calories_burned *
                self.exercise_db.get_exercise(ex['exercise_id']).duration_minutes
                for ex in selected_exercises
            ),
            'difficulty': self.user_profile.fitness_level.name,
            'goals_targeted': [goal.value for goal in self.user_profile.goals]
        }
    
    def provide_feedback(self, exercise_id: str, satisfaction_score: float):
        """
        Record user feedback on a recommendation
        
        Args:
            exercise_id: ID of exercise
            satisfaction_score: User satisfaction (0-10)
        """
        if not 0 <= satisfaction_score <= 10:
            raise ValueError("Satisfaction score must be between 0 and 10")
        
        self.user_feedback[exercise_id] = satisfaction_score
        try:
            self._save_persistence()
        except Exception:
            pass

    def record_completion(self, exercise_id: str, satisfaction_score: float = None) -> Dict[str, Any]:
        """
        Record that the user completed an exercise. Computes the reward (using
        the environment logic) and appends a completion entry to
        `recommendation_history`.

        Args:
            exercise_id: ID of the completed exercise
            satisfaction_score: Optional user-reported satisfaction (0-10). If
               not provided, a simulated satisfaction will be computed.

        Returns:
            A dict with keys: exercise_id, simulated_satisfaction, reward, timestamp
        """
        from datetime import datetime
        from exercise_env import ExerciseRecommendationEnv

        ex = self.exercise_db.get_exercise(exercise_id)
        if ex is None:
            raise ValueError(f"Exercise {exercise_id} not found")

        # Create temp env to compute simulated satisfaction / reward
        try:
            temp_env = ExerciseRecommendationEnv(self.user_profile, self.exercise_db)
        except Exception:
            temp_env = None

        # Use provided satisfaction if given, otherwise simulate
        if satisfaction_score is None:
            if temp_env is not None:
                sim_satisfaction = float(temp_env._simulate_user_feedback(ex))
            else:
                sim_satisfaction = None
        else:
            sim_satisfaction = float(satisfaction_score)

        # Compute reward using environment logic
        sim_reward = None
        try:
            if temp_env is not None and sim_satisfaction is not None:
                sim_reward = float(temp_env._calculate_reward(ex, sim_satisfaction))
        except Exception:
            sim_reward = None

        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'exercise_id': exercise_id,
            'exercise_name': ex.name,
            'completed': True,
            'satisfaction': sim_satisfaction,
            'reward': sim_reward
        }

        # Append to history
        try:
            self.recommendation_history.append(entry)
        except Exception:
            pass

        try:
            self._save_persistence()
        except Exception:
            pass

        # Also store feedback if provided
        if sim_satisfaction is not None:
            self.user_feedback[exercise_id] = sim_satisfaction

        # Return the recorded entry
        return entry
    
    def get_recommendation_history(self) -> List[Dict]:
        """Get history of all recommendations"""
        return self.recommendation_history.copy()

    # ---------------------------- Persistence ----------------------------
    def _history_file_path(self) -> Path:
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        return data_dir / f"{self.user_id}_history.json"

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
            'recommendation_history': self.recommendation_history,
            'user_feedback': self.user_feedback
        }
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)
    
    def _get_user_state(self) -> np.ndarray:
        """Get current user state for agent"""
        state = np.zeros(15, dtype=np.float32)
        
        # User features
        state[0] = self.user_profile.age / 100
        state[1] = self.user_profile.fitness_level.value / 3
        state[2] = self.user_profile.available_time / 120
        state[3] = len(self.user_profile.goals) / 5
        
        # Recent feedback
        if self.user_feedback:
            feedback_scores = list(self.user_feedback.values())[-5:]
            for i, score in enumerate(feedback_scores):
                state[9 + i] = score / 10
        
        return state
    
    def _build_timed_workout(self, available_time_minutes: int, use_exploration: bool = False) -> List[Dict[str, Any]]:
        """
        Build a workout session that fits within the available time
        
        Args:
            available_time_minutes: Total time available for workout
            use_exploration: Whether to use exploration in action selection
            
        Returns:
            List of exercises that fit the available time
        """
        recommendations = []
        remaining_time = available_time_minutes
        
        # Get best actions from agent
        best_actions = self._get_best_actions(len(self.suitable_exercises))
        
        # Build workout by selecting exercises that fit remaining time
        rank = 1
        for action_idx in best_actions:
            if remaining_time <= 0:
                break
                
            exercise = self.suitable_exercises[action_idx]
            
            # If this exercise fits entirely, add it
            if exercise.duration_minutes <= remaining_time:
                rec = {
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
                    'rationale': self._generate_rationale(exercise),
                    'total_calories': exercise.duration_minutes * exercise.calories_burned
                }
                recommendations.append(rec)
                remaining_time -= exercise.duration_minutes
                rank += 1
        
        # If no exercises fit, try to find shorter ones
        if not recommendations and self.suitable_exercises:
            # Sort by duration and add shortest exercises first
            sorted_exs = sorted(enumerate(self.suitable_exercises), 
                              key=lambda x: x[1].duration_minutes)
            for idx, exercise in sorted_exs:
                if remaining_time <= 0:
                    break
                if exercise.duration_minutes <= remaining_time:
                    rec = {
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
                        'rationale': self._generate_rationale(exercise),
                        'total_calories': exercise.duration_minutes * exercise.calories_burned
                    }
                    recommendations.append(rec)
                    remaining_time -= exercise.duration_minutes
                    rank += 1
        
        # Record to history
        try:
            from datetime import datetime
            timestamp = datetime.utcnow().isoformat()
            for rec in recommendations:
                entry = {
                    'timestamp': timestamp,
                    'exercise_id': rec['exercise_id'],
                    'exercise_name': rec['exercise_name'],
                    'duration_minutes': rec['duration_minutes'],
                    'total_calories': rec.get('total_calories', 0)
                }
                self.recommendation_history.append(entry)
            self._save_persistence()
        except Exception:
            pass
        
        return recommendations
    
    def _get_best_actions(self, num_actions: int) -> np.ndarray:
        """Get best actions from agent"""
        state_tensor = self._get_user_state()
        
        import torch
        state_t = torch.FloatTensor(state_tensor).unsqueeze(0)
        
        with torch.no_grad():
            q_values = self.agent.q_network(state_t).squeeze(0)
        
        # Get top k actions
        # Only use Q-values for available exercises
        num_exercises = len(self.suitable_exercises)
        q_values = q_values[:num_exercises]  # Truncate to match actual exercise count
        
        # Get top k actions
        top_k = min(num_actions, num_exercises)
        if top_k > 0:
            _, top_actions = torch.topk(q_values, top_k)
            return top_actions.numpy().astype(int)
        else:
            return np.array([])
    
    def _generate_rationale(self, exercise: Exercise) -> str:
        """Generate explanation for why exercise is recommended"""
        reasons = []
        
        # Check goal alignment
        for goal in self.user_profile.goals:
            if goal.value == "weight_loss" and exercise.intensity_level >= 6:
                reasons.append(f"Aligns with your {goal.value} goal")
            elif goal.value == "muscle_gain" and exercise.intensity_level >= 5:
                reasons.append(f"Aligns with your {goal.value} goal")
            elif goal.value == "endurance" and exercise.exercise_id in ["walking", "jogging"]:
                reasons.append(f"Aligns with your {goal.value} goal")
        
        # Check if it's a preferred exercise
        if exercise.name in self.user_profile.preferred_exercises:
            reasons.append("One of your preferred exercises")
        
        # Check difficulty appropriateness
        if exercise.difficulty == self.user_profile.fitness_level:
            reasons.append("Appropriate for your fitness level")
        
        # Check time fit
        if abs(exercise.duration_minutes - self.user_profile.available_time) < 15:
            reasons.append("Fits your available time")
        
        if not reasons:
            reasons.append("Well-suited based on your profile")
        
        return " • ".join(reasons)

    def get_safety_info(self, exercise_id: str) -> Dict[str, Any]:
        """
        Compute safety and recommendation metadata for an exercise given the
        current user profile.

        Returns a dict with keys:
          - best_exercise_type: 'cardio'|'strength'|'flexibility'|'core'|'general'
          - recommended_intensity: int (1-10)
          - safe_duration: float (minutes)
          - unsafe: bool
          - notes: brief explanation
        """
        ex = self.exercise_db.get_exercise(exercise_id)

        # Determine best exercise type
        pg = {m.value for m in ex.primary_muscles}
        if 'cardio' in pg:
            best_type = 'cardio'
        elif any(m in pg for m in ['chest', 'back', 'biceps', 'triceps', 'shoulders', 'forearms', 'quadriceps', 'glutes', 'hamstrings', 'calves']):
            best_type = 'strength'
        elif 'abs' in pg:
            best_type = 'core'
        else:
            best_type = 'flexibility' if ex.intensity_level <= 3 else 'general'

        # Base intensity and adjustments
        base_int = ex.intensity_level
        fatigue = getattr(self.user_profile, 'fatigue', 0.0)
        soreness = getattr(self.user_profile, 'soreness', 0.0)
        sleep_hours = getattr(self.user_profile, 'sleep_hours', 8.0)
        resting_hr = getattr(self.user_profile, 'resting_heart_rate', 60)
        age = getattr(self.user_profile, 'age', 30)

        # Reduce intensity when fatigue or soreness present
        intensity_penalty = int(round((fatigue + soreness) / 5.0))
        rec_intensity = max(1, base_int - intensity_penalty)

        # If resting HR is high, lower intensity
        if resting_hr and resting_hr >= 100:
            rec_intensity = max(1, rec_intensity - 2)

        # Older users -> cap intensity
        if age >= 65:
            rec_intensity = min(rec_intensity, 5)

        # Safe duration: start from exercise duration then reduce per conditions
        safe_dur = ex.duration_minutes
        if fatigue >= 8 or soreness >= 8:
            safe_dur = max(5, safe_dur * 0.5)
        if sleep_hours < 5:
            safe_dur = max(5, safe_dur * 0.7)
        if age >= 65 and ex.intensity_level >= 7:
            safe_dur = max(5, safe_dur * 0.7)

        # Determine unsafe flag (contraindications & intensity vs conditions)
        unsafe = False
        notes = []
        # Contraindications
        for inj in self.user_profile.injuries:
            if inj in ex.contraindications:
                unsafe = True
                notes.append(f"Contraindicated for {inj}")

        # High intensity when user is fatigued/sore
        if base_int >= 8 and (fatigue >= 6 or soreness >= 6):
            unsafe = True
            notes.append("High intensity not recommended when fatigued/sore")

        # High resting HR
        if resting_hr >= 110 and base_int >= 7:
            unsafe = True
            notes.append("High resting heart rate — reduce intensity")

        if not notes:
            notes = ["Suitable with caution"]

        return {
            'best_exercise_type': best_type,
            'recommended_intensity': int(rec_intensity),
            'safe_duration': float(round(safe_dur, 1)),
            'unsafe': unsafe,
            'notes': "; ".join(notes)
        }


class RecommendationSystem:
    """Complete recommendation system with user management"""
    
    def __init__(self, agent_path: str = None):
        """
        Initialize recommendation system
        
        Args:
            agent_path: Path to trained agent (optional)
        """
        self.exercise_db = ExerciseDatabase()
        self.user_manager = UserProfileManager()
        
        # Load or initialize agent. Ensure agent action_size matches the
        # current exercise database size so network outputs map to exercises.
        total_exercises = len(self.exercise_db.get_all_exercises())
        if agent_path and os.path.exists(agent_path):
            # initialize with current DB action size, then load weights (loader will map/pad fc3)
            self.agent = DQNAgent(state_size=15, action_size=total_exercises)
            self.agent.load(agent_path)
        else:
            # Use untrained agent for new users; action_size equals total exercises
            self.agent = DQNAgent(state_size=15, action_size=total_exercises)
        
        self.recommenders: Dict[str, ExerciseRecommender] = {}
    
    def register_user(self, user_profile: UserProfile) -> ExerciseRecommender:
        """
        Register a user and create their recommender
        
        Args:
            user_profile: User's fitness profile
            
        Returns:
            ExerciseRecommender for this user
        """
        self.user_manager.create_profile(user_profile)
        
        recommender = ExerciseRecommender(
            agent=self.agent,
            exercise_db=self.exercise_db,
            user_id=user_profile.user_id,
            user_profile=user_profile
        )
        
        self.recommenders[user_profile.user_id] = recommender
        return recommender
    
    def get_recommender(self, user_id: str) -> ExerciseRecommender:
        """Get recommender for a user"""
        if user_id not in self.recommenders:
            raise ValueError(f"User {user_id} not registered")
        return self.recommenders[user_id]
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user's profile"""
        return self.user_manager.get_profile(user_id)
