"""
Reinforcement Learning Environment for Exercise Recommendations
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Tuple, Dict, Any
from exercise_database import ExerciseDatabase, ExerciseDifficulty
from user_profile import UserProfile, FitnessLevel


class ExerciseRecommendationEnv(gym.Env):
    """
    Gym environment for RL-based exercise recommendations
    
    State: User fitness profile features + previous exercise interaction history
    Action: Index of exercise to recommend
    Reward: Based on user satisfaction, goal alignment, injury safety
    """
    
    metadata = {"render_modes": ["human"]}
    
    def __init__(self, user_profile: UserProfile, exercise_db: ExerciseDatabase):
        """
        Initialize the environment
        
        Args:
            user_profile: The user's fitness profile
            exercise_db: Exercise database
        """
        self.user_profile = user_profile
        self.exercise_db = exercise_db
        
        # Get suitable exercises for this user
        self.suitable_exercises = exercise_db.get_suitable_exercises(
            injuries=user_profile.injuries,
            available_equipment=user_profile.equipment_access,
            difficulty=user_profile.fitness_level
        )
        
        if not self.suitable_exercises:
            raise ValueError("No suitable exercises found for this user")
        
        # Action space: select from available exercises
        self.action_space = spaces.Discrete(len(self.suitable_exercises))
        
        # Observation space: user state features
        # Features: age, fitness_level, available_time, num_goals, 
        #           exercise_history (last 5 exercises), user_satisfaction
        self.observation_space = spaces.Box(
            low=0, high=100,
            shape=(15,),  # 1 age + 1 fitness + 1 time + 1 goals + 
                          # 5 recent exercises + 5 satisfaction scores + 1 streak
            dtype=np.float32
        )
        
        # Initialize tracking
        self.exercise_history: Dict[str, int] = {}  # count of times recommended
        self.user_feedback: Dict[str, float] = {}   # user satisfaction scores
        self.steps = 0
        self.max_steps = 30  # max recommendations per episode
        self.current_observation = self._get_observation()
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation of user state"""
        obs = np.zeros(15, dtype=np.float32)
        
        # User features
        obs[0] = self.user_profile.age / 100  # normalize to 0-1
        obs[1] = self.user_profile.fitness_level.value / 3  # 1-3 normalized
        obs[2] = self.user_profile.available_time / 120  # normalize
        obs[3] = len(self.user_profile.goals) / 5  # max 5 goals
        
        # Recent exercise history (last 5)
        recent_exercises = sorted(
            self.exercise_history.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for i, (exercise_id, count) in enumerate(recent_exercises):
            # Normalize exercise index
            exercise_idx = self.suitable_exercises.index(
                self.exercise_db.get_exercise(exercise_id)
            )
            obs[4 + i] = exercise_idx / max(len(self.suitable_exercises), 1)
        
        # Recent feedback scores (last 5)
        recent_feedback = sorted(
            self.user_feedback.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for i, (exercise_id, score) in enumerate(recent_feedback):
            obs[9 + i] = score / 10  # normalize to 0-1
        
        # Consistency streak
        if len(self.exercise_history) > 0:
            obs[14] = len(self.exercise_history) / 20
        
        return obs
    
    def reset(self, seed=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset the environment"""
        super().reset(seed=seed)
        self.steps = 0
        self.current_observation = self._get_observation()
        return self.current_observation, {}
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one step in the environment
        
        Args:
            action: Index of exercise to recommend
            
        Returns:
            observation, reward, terminated, truncated, info
        """
        self.steps += 1
        
        # Get recommended exercise
        if action < 0 or action >= len(self.suitable_exercises):
            raise ValueError(f"Invalid action {action}")
        
        recommended_exercise = self.suitable_exercises[action]
        exercise_id = recommended_exercise.exercise_id
        
        # Update history
        if exercise_id not in self.exercise_history:
            self.exercise_history[exercise_id] = 0
        self.exercise_history[exercise_id] += 1
        
        # Simulate user feedback (would come from actual user in production)
        user_satisfaction = self._simulate_user_feedback(recommended_exercise)
        self.user_feedback[exercise_id] = user_satisfaction
        
        # Calculate reward
        reward = self._calculate_reward(recommended_exercise, user_satisfaction)
        
        # Get next observation
        next_observation = self._get_observation()
        
        # Check termination
        terminated = self.steps >= self.max_steps
        truncated = False
        
        info = {
            "exercise_id": exercise_id,
            "exercise_name": recommended_exercise.name,
            "user_satisfaction": user_satisfaction,
            "reward": reward
        }
        
        self.current_observation = next_observation
        
        return next_observation, float(reward), terminated, truncated, info
    
    def _simulate_user_feedback(self, exercise: Any) -> float:
        """
        Simulate user satisfaction feedback
        In production, this would come from actual user interaction
        
        Score: 0-10
        """
        score = 5.0  # base score
        
        # Bonus for intensity match
        if self.user_profile.fitness_level == FitnessLevel.BEGINNER:
            if exercise.intensity_level <= 4:
                score += 2
            elif exercise.intensity_level > 7:
                score -= 2
        elif self.user_profile.fitness_level == FitnessLevel.INTERMEDIATE:
            if 4 <= exercise.intensity_level <= 7:
                score += 2
        else:  # ADVANCED
            if exercise.intensity_level >= 7:
                score += 2
        
        # Bonus for time fit
        if abs(exercise.duration_minutes - self.user_profile.available_time) < 10:
            score += 1
        
        # Bonus for preferred exercises
        if exercise.name in self.user_profile.preferred_exercises:
            score += 2
        
        # Penalty for repetition (encourage variety)
        if exercise.exercise_id in self.user_feedback:
            repeat_count = self.exercise_history[exercise.exercise_id]
            if repeat_count > 3:
                score -= 1 * (repeat_count - 3)
        
        # Add some randomness
        score += np.random.normal(0, 0.5)
        
        # Clamp to 0-10
        return np.clip(score, 0, 10)
    
    def _calculate_reward(self, exercise: Any, user_satisfaction: float) -> float:
        """
        Calculate reward based on exercise recommendation quality
        
        Factors:
        - User satisfaction
        - Goal alignment
        - Difficulty appropriate for fitness level
        - Safety (no contraindications)
        - Variety (not repeating same exercise too often)
        """
        # Implement reward logic based on daily user conditions.
        # Primary outcomes:
        #  - Safe recommendations => +1..+3
        #  - Unsafe recommendations => -5
        #  - Balanced/neutral => small reward 0..+1

        reward = 0.0

        # Read daily metrics from profile
        fatigue = getattr(self.user_profile, 'fatigue', 0.0)
        soreness = getattr(self.user_profile, 'soreness', 0.0)
        sleep_hours = getattr(self.user_profile, 'sleep_hours', 8.0)
        resting_hr = getattr(self.user_profile, 'resting_heart_rate', 60)
        age = getattr(self.user_profile, 'age', 30)

        intensity = getattr(exercise, 'intensity_level', 5)

        # Safety checks (hard negatives)
        high_fatigue = fatigue >= 7.0
        high_soreness = soreness >= 7.0
        poor_sleep = sleep_hours <= 5.0
        high_rest_hr = resting_hr >= 100
        older_user = age >= 65

        # Unsafe: vigorous/intense when user is in poor condition
        if (high_fatigue or high_soreness) and intensity >= 6:
            return -5.0

        if poor_sleep and intensity >= 7:
            return -5.0

        if high_rest_hr and intensity >= 6:
            return -5.0

        if older_user and intensity >= 8:
            # strong negative for very high intensity in older users
            return -5.0

        # Injury-specific contraindications (hard negatives)
        # Map common injuries to exercise IDs that should be avoided
        contraindications = {
            'lower_back_pain': ['deadlift', 'squats', 'bent_over_row'],
            'knee_pain': ['jumping', 'box_jumps', 'lunges', 'squats'],
            'shoulder_pain': ['overhead_press', 'pull_ups', 'bench_press'],
        }

        for injury in getattr(self.user_profile, 'injuries', []) or []:
            inj_key = injury.lower()
            if inj_key in contraindications:
                bad_list = contraindications[inj_key]
                if exercise.exercise_id in bad_list:
                    return -5.0

        # Safe recommendations: match intensity to condition
        # If user is well-rested and not sore, moderate/vigorous recommended
        if (fatigue <= 3.0 and soreness <= 3.0) and intensity >= 5:
            # positive reward scaled by user_satisfaction (0-10 -> 0-1) plus base
            reward += 2.0 + min(max((user_satisfaction - 5.0) / 5.0, 0.0), 1.0)
            # cap at +3
            reward = min(reward, 3.0)
            # Add goal alignment bonus below

        # If user is fatigued/sore but exercise is light, it's appropriate
        elif (high_fatigue or high_soreness) and intensity <= 4:
            reward += 1.5 + min(max((user_satisfaction - 5.0) / 10.0, 0.0), 0.5)

        else:
            # Balanced/middle cases: small reward proportional to satisfaction (0..1)
            reward += max(0.0, min(user_satisfaction / 10.0, 1.0))

        # Goal alignment bonus (small)
        relevant_goals = 0
        for goal in self.user_profile.goals:
            if goal.value == "endurance" and exercise.exercise_id in ["walking", "jogging"]:
                relevant_goals += 1
            elif goal.value == "weight_loss" and intensity >= 6:
                relevant_goals += 1
            elif goal.value == "muscle_gain" and intensity >= 5:
                relevant_goals += 1
            elif goal.value == "flexibility" and exercise.exercise_id in ["yoga", "stretching"]:
                relevant_goals += 1

        reward += relevant_goals * 0.5

        # Penalty for excessive repetition (moderate)
        repeat_count = self.exercise_history.get(exercise.exercise_id, 0)
        if repeat_count > 3:
            reward -= 0.5 * (repeat_count - 3)

        # Bonus for variety (small)
        unique_exercises = len(self.exercise_history)
        reward += min(unique_exercises * 0.05, 1.0)

        # Clamp reward to reasonable bounds
        reward = float(np.clip(reward, -5.0, 5.0))
        return reward
    
    def render(self, mode="human"):
        """Render the environment"""
        if mode == "human":
            print(f"Step: {self.steps}")
            print(f"Exercise history: {self.exercise_history}")
            print(f"User feedback: {self.user_feedback}")
    
    def get_action_name(self, action: int) -> str:
        """Get the name of an action"""
        return self.suitable_exercises[action].name
