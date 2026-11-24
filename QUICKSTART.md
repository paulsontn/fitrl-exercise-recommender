"""
Quick Start Guide - RL Exercise Recommendation System
"""

# ============================================================================
# STEP 1: INSTALLATION
# ============================================================================

# Install all dependencies
pip install -r requirements.txt

# ============================================================================
# STEP 2: TRAIN THE AGENT
# ============================================================================

python main.py

# This will:
# 1. Analyze the exercise database
# 2. Train a DQN agent for 100 episodes
# 3. Generate training curves (training_curves.png)
# 4. Save trained agent (trained_agent.pt)
# 5. Demo the recommendation system

# ============================================================================
# STEP 3: USE THE RECOMMENDATION SYSTEM
# ============================================================================

from user_profile import UserProfile, FitnessLevel, UserGoal
from recommendation_system import RecommendationSystem

# Initialize with trained agent
system = RecommendationSystem(agent_path="trained_agent.pt")

# Create a user profile
user = UserProfile(
    user_id="john_doe_001",
    age=30,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
    available_time=45,
    injuries=[],
    equipment_access=["dumbbells", "barbell", "bench"],
    preferred_exercises=["bench_press", "squats", "deadlifts"]
)

# Register the user
recommender = system.register_user(user)

# Get personalized recommendations
recommendations = recommender.get_recommendations(num_recommendations=5)

for rec in recommendations:
    print(f"{rec['rank']}. {rec['exercise_name']}")
    print(f"   Duration: {rec['duration_minutes']} min")
    print(f"   Intensity: {rec['intensity_level']}/10")
    print(f"   Why: {rec['rationale']}\n")

# Get a full workout plan
workout = recommender.recommend_personalized_workout(session_duration=45)
print(f"Personalized Workout ({workout['total_duration']} min):")
for i, ex in enumerate(workout['exercises'], 1):
    print(f"  {i}. {ex['exercise_name']} ({ex['duration_minutes']} min)")

# ============================================================================
# STEP 4: START THE API SERVER
# ============================================================================

python api.py

# Server runs on http://localhost:5000

# Example API calls:

# 1. Register a user
# POST http://localhost:5000/api/users/register
# {
#     "user_id": "alice_smith",
#     "age": 28,
#     "fitness_level": "BEGINNER",
#     "goals": ["weight_loss", "general_fitness"],
#     "available_time": 30,
#     "equipment_access": []
# }

# 2. Get recommendations
# GET http://localhost:5000/api/recommendations/alice_smith?num_recommendations=5

# 3. Get personalized workout
# GET http://localhost:5000/api/workout/alice_smith?duration=30

# 4. Submit user feedback
# POST http://localhost:5000/api/feedback/alice_smith
# {
#     "exercise_id": "squats",
#     "satisfaction_score": 8.5
# }

# ============================================================================
# STEP 5: EVALUATE THE SYSTEM
# ============================================================================

python evaluation.py

# This will:
# 1. Test goal alignment
# 2. Check safety (injury contraindications)
# 3. Evaluate diversity
# 4. Measure time fit
# 5. Assess difficulty matching
# 6. Generate overall performance score

# ============================================================================
# CUSTOMIZATION EXAMPLES
# ============================================================================

# Example 1: Add a new exercise to the database
from exercise_database import ExerciseDatabase, Exercise, MuscleGroup, ExerciseDifficulty

db = ExerciseDatabase()

new_exercise = Exercise(
    exercise_id="swimming",
    name="Swimming",
    description="Full-body cardio and strength exercise",
    primary_muscles={MuscleGroup.CARDIO, MuscleGroup.BACK},
    secondary_muscles={MuscleGroup.CHEST, MuscleGroup.SHOULDERS},
    difficulty=ExerciseDifficulty.INTERMEDIATE,
    duration_minutes=30,
    equipment_required=["pool"],
    intensity_level=7,
    calories_burned=10,
    contraindications=[]
)

db.add_exercise(new_exercise)

# Example 2: Update user profile after some time
from user_profile import UserProfileManager

manager = UserProfileManager()
manager.create_profile(user)

# User improved their fitness level
manager.update_fitness_level("john_doe_001", FitnessLevel.ADVANCED)

# Example 3: Handle user injuries
manager.add_injury("john_doe_001", "shoulder_pain")
recommendations = recommender.get_recommendations()  # Will exclude shoulder exercises

# Remove injury once recovered
manager.remove_injury("john_doe_001", "shoulder_pain")

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

# user_profile.py
#   ├── FitnessLevel (BEGINNER, INTERMEDIATE, ADVANCED)
#   ├── UserGoal (WEIGHT_LOSS, MUSCLE_GAIN, ENDURANCE, FLEXIBILITY, GENERAL_FITNESS)
#   ├── UserProfile (age, fitness_level, goals, injuries, equipment, preferences)
#   └── UserProfileManager

# exercise_database.py
#   ├── MuscleGroup (CHEST, BACK, SHOULDERS, etc.)
#   ├── ExerciseDifficulty
#   ├── Exercise (id, name, description, muscles, difficulty, duration, etc.)
#   └── ExerciseDatabase (15+ pre-loaded exercises)

# exercise_env.py
#   └── ExerciseRecommendationEnv (Gym environment for RL training)

# rl_agent.py
#   ├── QNetwork (Deep Q-Network)
#   ├── PolicyNetwork (Policy gradient network)
#   ├── DQNAgent (Value-based learning)
#   └── PolicyGradientAgent (Policy optimization)

# trainer.py
#   ├── ExerciseRecommendationTrainer (DQN training)
#   └── PolicyGradientTrainer (REINFORCE training)

# recommendation_system.py
#   ├── ExerciseRecommender (Per-user recommender)
#   └── RecommendationSystem (Manages multiple users)

# api.py
#   └── Flask REST API with endpoints:
#       ├── POST /api/users/register
#       ├── GET /api/users/<user_id>
#       ├── GET /api/recommendations/<user_id>
#       ├── GET /api/workout/<user_id>
#       ├── POST /api/feedback/<user_id>
#       └── GET /api/exercises

# evaluation.py
#   └── SystemEvaluator (Comprehensive system evaluation)

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Q: "No suitable exercises found for this user"
# A: Check that user's injuries and equipment_access are correct

# Q: ModuleNotFoundError: No module named 'torch'
# A: Run: pip install -r requirements.txt

# Q: Port 5000 is already in use
# A: Change port in api.py or kill existing process:
#    On Windows: netstat -ano | findstr :5000
#    On Linux: lsof -i :5000

# Q: Agent not learning well
# A: Adjust learning_rate, gamma, or network hidden_size in config.py
#    Or increase training episodes in main.py

# ============================================================================
# PERFORMANCE TIPS
# ============================================================================

# 1. More training episodes → Better recommendations
#    Modify: trainer.train(num_episodes=200)

# 2. Larger neural networks → Better generalization
#    In rl_agent.py: hidden_size=256

# 3. Incorporate real user feedback
#    Use: recommender.provide_feedback(exercise_id, satisfaction_score)

# 4. Periodic retraining
#    Retrain agent monthly with accumulated user feedback

# ============================================================================
