"""
EXAMPLES - How to Use the RL Exercise Recommendation System
"""

# ============================================================================
# EXAMPLE 1: Simple Recommendation
# ============================================================================

from user_profile import UserProfile, FitnessLevel, UserGoal
from recommendation_system import RecommendationSystem

# Initialize system
system = RecommendationSystem()

# Create a user profile
user = UserProfile(
    user_id="john_123",
    age=30,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
    available_time=45,
    injuries=[],
    equipment_access=["dumbbells", "barbell", "bench"],
    preferred_exercises=["bench_press", "squats"]
)

# Register and get recommendations
recommender = system.register_user(user)
recommendations = recommender.get_recommendations(num_recommendations=5)

# Print recommendations
for rec in recommendations:
    print(f"{rec['rank']}. {rec['exercise_name']}")
    print(f"   Duration: {rec['duration_minutes']}min | Intensity: {rec['intensity_level']}/10")
    print(f"   Why: {rec['rationale']}\n")


# ============================================================================
# EXAMPLE 2: Generating a Personalized Workout Plan
# ============================================================================

# Generate a 45-minute workout
workout = recommender.recommend_personalized_workout(session_duration=45)

print(f"Personalized Workout Plan")
print(f"Total Duration: {workout['total_duration']} minutes")
print(f"Estimated Calories: {workout['estimated_calories']:.0f}")
print(f"Goals: {', '.join(workout['goals_targeted'])}")
print(f"\nExercises:")

for i, exercise in enumerate(workout['exercises'], 1):
    print(f"  {i}. {exercise['exercise_name']} ({exercise['duration_minutes']} min)")


# ============================================================================
# EXAMPLE 3: Multiple Users with Different Profiles
# ============================================================================

users = [
    UserProfile(
        user_id="alice",
        age=25,
        fitness_level=FitnessLevel.BEGINNER,
        goals=[UserGoal.GENERAL_FITNESS],
        available_time=30,
        injuries=[],
        equipment_access=[],
        preferred_exercises=["walking", "stretching"]
    ),
    UserProfile(
        user_id="bob",
        age=35,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN],
        available_time=60,
        injuries=["lower_back_pain"],
        equipment_access=["dumbbells", "barbell"],
        preferred_exercises=[]
    ),
    UserProfile(
        user_id="carol",
        age=28,
        fitness_level=FitnessLevel.ADVANCED,
        goals=[UserGoal.MUSCLE_GAIN, UserGoal.STRENGTH],
        available_time=90,
        injuries=[],
        equipment_access=["dumbbells", "barbell", "bench", "pull_up_bar"],
        preferred_exercises=["deadlifts", "pull_ups", "bench_press"]
    )
]

# Get recommendations for each user
for user_profile in users:
    recommender = system.register_user(user_profile)
    recommendations = recommender.get_recommendations(num_recommendations=3)
    
    print(f"\n{user_profile.user_id.upper()}'s Recommendations:")
    for rec in recommendations:
        print(f"  • {rec['exercise_name']}")


# ============================================================================
# EXAMPLE 4: Handling User Injuries
# ============================================================================

from user_profile import UserProfileManager

# User with existing injury
injured_user = UserProfile(
    user_id="dave",
    age=40,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.WEIGHT_LOSS],
    available_time=45,
    injuries=["knee_pain"],  # Can't do running, jumping
    equipment_access=["dumbbells"],
    preferred_exercises=[]
)

recommender = system.register_user(injured_user)
recommendations = recommender.get_recommendations(num_recommendations=5)

print("Exercises Safe for Knee Pain:")
for rec in recommendations:
    print(f"  ✓ {rec['exercise_name']} - {rec['rationale']}")


# ============================================================================
# EXAMPLE 5: User Feedback Integration
# ============================================================================

# Get initial recommendations
recommendations = recommender.get_recommendations(num_recommendations=5)

# User tries exercises and provides feedback
feedback = {
    recommendations[0]['exercise_id']: 9.0,  # Loved it!
    recommendations[1]['exercise_id']: 7.0,  # Good
    recommendations[2]['exercise_id']: 5.0,  # Okay
}

# Record feedback
for exercise_id, score in feedback.items():
    recommender.provide_feedback(exercise_id, score)
    print(f"Recorded feedback for {exercise_id}: {score}/10")

# Next recommendations will adapt based on feedback
# In production, the agent would retrain on this feedback


# ============================================================================
# EXAMPLE 6: Accessing the Exercise Database
# ============================================================================

from exercise_database import ExerciseDatabase, MuscleGroup, ExerciseDifficulty

db = ExerciseDatabase()

# Get all exercises
all_exercises = db.get_all_exercises()
print(f"Total exercises: {len(all_exercises)}")

# Filter by difficulty
beginner_exercises = db.filter_by_difficulty(ExerciseDifficulty.BEGINNER)
print(f"Beginner exercises: {len(beginner_exercises)}")

# Filter by muscle group
chest_exercises = db.filter_by_muscle_group(MuscleGroup.CHEST)
print(f"Chest exercises: {len(chest_exercises)}")

# Get suitable exercises for a user
suitable = db.get_suitable_exercises(
    injuries=["knee_pain"],
    available_equipment=["dumbbells"],
    difficulty=ExerciseDifficulty.BEGINNER
)
print(f"Suitable exercises: {len(suitable)}")


# ============================================================================
# EXAMPLE 7: Training the Agent (Optional)
# ============================================================================

from exercise_env import ExerciseRecommendationEnv
from rl_agent import DQNAgent
from trainer import ExerciseRecommendationTrainer

# Create training user
training_user = UserProfile(
    user_id="training_user",
    age=30,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
    available_time=45,
    injuries=[],
    equipment_access=["dumbbells", "barbell", "bench", "pull_up_bar"],
    preferred_exercises=["bench_press", "squats", "deadlifts"]
)

# Create environment and agent
db = ExerciseDatabase()
env = ExerciseRecommendationEnv(training_user, db)
agent = DQNAgent(
    state_size=15,
    action_size=len(env.suitable_exercises),
    learning_rate=0.001
)

# Train agent
trainer = ExerciseRecommendationTrainer(agent, env)
rewards, lengths = trainer.train(num_episodes=50)  # Train on 50 episodes

# Save trained agent
agent.save("my_trained_agent.pt")

print(f"Training complete! Final reward: {rewards[-1]:.2f}")


# ============================================================================
# EXAMPLE 8: REST API Usage (requires api.py running)
# ============================================================================

import requests
import json

API_URL = "http://localhost:5000"

# 1. Register a user
user_data = {
    "user_id": "api_user_001",
    "age": 30,
    "fitness_level": "INTERMEDIATE",
    "goals": ["muscle_gain", "weight_loss"],
    "available_time": 45,
    "equipment_access": ["dumbbells", "barbell"],
    "preferred_exercises": ["bench_press"]
}

response = requests.post(f"{API_URL}/api/users/register", json=user_data)
print(f"Registration: {response.json()}")

# 2. Get recommendations
response = requests.get(
    f"{API_URL}/api/recommendations/api_user_001",
    params={"num_recommendations": 5}
)
print(f"Recommendations: {len(response.json()['recommendations'])} exercises")

# 3. Get workout plan
response = requests.get(
    f"{API_URL}/api/workout/api_user_001",
    params={"duration": 45}
)
workout = response.json()
print(f"Workout: {len(workout['exercises'])} exercises, {workout['total_duration']} min")

# 4. Submit feedback
feedback_data = {
    "exercise_id": "bench_press",
    "satisfaction_score": 8.5
}
response = requests.post(
    f"{API_URL}/api/feedback/api_user_001",
    json=feedback_data
)
print(f"Feedback recorded: {response.json()}")

# 5. List all exercises
response = requests.get(f"{API_URL}/api/exercises")
print(f"Available exercises: {response.json()['total']}")


# ============================================================================
# EXAMPLE 9: System Evaluation
# ============================================================================

from evaluation import SystemEvaluator

evaluator = SystemEvaluator()
metrics = evaluator.run_full_evaluation(num_users=10)

print(f"\nSystem Performance:")
print(f"  Safety: {metrics['safety']['safety_rate']:.2%}")
print(f"  Goal Alignment: {metrics['goal_alignment']['mean_alignment']:.2%}")
print(f"  Diversity: {metrics['diversity']['mean_diversity']:.2%}")
print(f"  Time Fit: {metrics['time_fit']['mean_time_fit']:.2%}")
print(f"  Difficulty: {metrics['difficulty']['difficulty_match_rate']:.2%}")


# ============================================================================
# EXAMPLE 10: Custom Configuration
# ============================================================================

from config import RL_CONFIG, TRAINING_CONFIG, RECOMMENDATION_CONFIG

# Print current configuration
print(f"Learning Rate: {RL_CONFIG['learning_rate']}")
print(f"Discount Factor: {RL_CONFIG['gamma']}")
print(f"Network Hidden Size: {RL_CONFIG['hidden_size']}")
print(f"Training Episodes: {TRAINING_CONFIG['num_episodes']}")
print(f"Default Recommendations: {RECOMMENDATION_CONFIG['default_num_recommendations']}")

# Modify configuration
RL_CONFIG['learning_rate'] = 0.0005  # Lower learning rate
RL_CONFIG['hidden_size'] = 256        # Larger network
TRAINING_CONFIG['num_episodes'] = 200  # More training


# ============================================================================
# EXAMPLE 11: Adding Custom Exercises
# ============================================================================

from exercise_database import Exercise, ExerciseDifficulty, MuscleGroup

db = ExerciseDatabase()

# Create a new exercise
swimming = Exercise(
    exercise_id="swimming",
    name="Swimming",
    description="Full-body cardio and low-impact exercise",
    primary_muscles={MuscleGroup.CARDIO, MuscleGroup.BACK},
    secondary_muscles={MuscleGroup.CHEST, MuscleGroup.SHOULDERS},
    difficulty=ExerciseDifficulty.INTERMEDIATE,
    duration_minutes=30,
    equipment_required=["pool"],
    intensity_level=7,
    calories_burned=10,
    contraindications=["shoulder_injury"]
)

# Add to database
db.add_exercise(swimming)

# Use in recommendations
print(f"Added exercise: {swimming.name}")


# ============================================================================
# EXAMPLE 12: Profile Management
# ============================================================================

from user_profile import UserProfileManager, UserGoal

manager = UserProfileManager()

# Create profile
user = UserProfile(
    user_id="profile_user",
    age=30,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.GENERAL_FITNESS],
    available_time=30,
    injuries=[],
    equipment_access=[],
    preferred_exercises=[]
)
manager.create_profile(user)

# Get profile
retrieved = manager.get_profile("profile_user")
print(f"Retrieved user: {retrieved.user_id}")

# Update fitness level
manager.update_fitness_level("profile_user", FitnessLevel.ADVANCED)

# Add goal
manager.add_goal("profile_user", UserGoal.MUSCLE_GAIN)

# Add injury
manager.add_injury("profile_user", "wrist_pain")

# Remove injury once healed
manager.remove_injury("profile_user", "wrist_pain")


# ============================================================================
# RUNNING THE EXAMPLES
# ============================================================================

"""
To run any of these examples:

1. Install dependencies:
   $ pip install -r requirements.txt

2. For examples 1-6, 9-12:
   Just run the example code in Python

3. For example 7 (training):
   $ python examples_7_training.py

4. For example 8 (REST API):
   - Terminal 1: python api.py
   - Terminal 2: python examples_8_api.py

5. For all examples together:
   $ python demo.py  (built-in demo with all examples)

"""
