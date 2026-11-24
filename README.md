# RL-Based Personalized Exercise Recommendation System

A comprehensive machine learning system that uses Reinforcement Learning to provide personalized exercise recommendations based on user profiles, fitness goals, and preferences.

## Features

### 1. **User Profile Management**
- Create and manage user fitness profiles
- Track fitness levels, goals, injuries, and equipment access
- Support for multiple fitness goals (muscle gain, weight loss, flexibility, etc.)

### 2. **Exercise Database**
- 15+ pre-configured exercises with detailed metadata
- Exercise properties: difficulty, duration, intensity, calories, target muscles
- Injury contraindications and equipment requirements
- Easily extensible for adding new exercises

### 3. **Reinforcement Learning Environment**
- Gym-based environment for RL training
- State space: user characteristics, exercise history, user feedback
- Action space: select from suitable exercises
- Reward function: user satisfaction, goal alignment, variety, safety

### 4. **RL Agents**
- **DQN (Deep Q-Network)**: Value-based learning with experience replay
- **Policy Gradient (REINFORCE)**: Direct policy optimization
- Both agents learn to maximize long-term user satisfaction

### 5. **Recommendation Engine**
- Personalized exercise recommendations using trained agent
- Explanation generation for each recommendation
- Workout plan generation based on available time
- User feedback integration for continuous improvement

### 6. **REST API**
- Flask-based API for easy integration
- User registration and profile management
- Get recommendations and personalized workouts
- Submit user feedback for agent improvement

## Project Structure

```
├── user_profile.py              # User profile classes
├── exercise_database.py         # Exercise database and definitions
├── exercise_env.py             # Gym environment for RL
├── rl_agent.py                 # DQN and Policy Gradient agents
├── trainer.py                  # Training loops
├── recommendation_system.py    # Main recommendation engine
├── main.py                     # Training and demo script
├── api.py                      # Flask REST API
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Key Libraries
- **numpy, pandas**: Data manipulation
- **torch**: Deep learning framework
- **gymnasium**: RL environment framework
- **flask**: REST API server
- **scikit-learn**: Machine learning utilities
- **matplotlib, seaborn**: Visualization

## Usage

### Training the Agent

```bash
python main.py
```

This will:
1. Create a sample user profile
2. Initialize the RL environment
3. Train a DQN agent for 100 episodes
4. Save the trained agent to `trained_agent.pt`
5. Demonstrate the recommendation system

### Using the Recommendation System

```python
from user_profile import UserProfile, FitnessLevel, UserGoal
from recommendation_system import RecommendationSystem

# Initialize system
system = RecommendationSystem(agent_path="trained_agent.pt")

# Create user profile
user = UserProfile(
    user_id="user_001",
    age=30,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
    available_time=45,
    injuries=[],
    equipment_access=["dumbbells", "barbell", "bench"],
    preferred_exercises=["bench_press", "squats"]
)

# Register user
recommender = system.register_user(user)

# Get recommendations
recommendations = recommender.get_recommendations(num_recommendations=5)

# Generate workout plan
workout = recommender.recommend_personalized_workout(session_duration=45)
```

### Running the REST API

```bash
python api.py
```

Server runs on `http://localhost:5000`

#### API Endpoints

**Register User**
```bash
POST /api/users/register
Content-Type: application/json

{
    "user_id": "user_001",
    "age": 30,
    "fitness_level": "INTERMEDIATE",
    "goals": ["muscle_gain", "weight_loss"],
    "available_time": 45,
    "injuries": [],
    "equipment_access": ["dumbbells", "barbell"],
    "preferred_exercises": ["bench_press", "squats"]
}
```

**Get Recommendations**
```bash
GET /api/recommendations/user_001?num_recommendations=5
```

**Get Personalized Workout**
```bash
GET /api/workout/user_001?duration=45
```

**Submit Feedback**
```bash
POST /api/feedback/user_001
Content-Type: application/json

{
    "exercise_id": "bench_press",
    "satisfaction_score": 8.5
}
```

**List All Exercises**
```bash
GET /api/exercises
```

## How It Works

### 1. **Environment Setup**
- User state is represented as a feature vector (age, fitness level, available time, goals, exercise history, user feedback)
- Actions are discrete indices representing exercises suitable for the user
- Rewards are calculated based on user satisfaction, goal alignment, and variety

### 2. **Training Process**
- Agent interacts with environment by recommending exercises
- User satisfaction is simulated based on exercise properties
- DQN learns to maximize cumulative reward through Q-learning
- Experience replay and target networks stabilize training

### 3. **Recommendation Generation**
- At inference time, user state is encoded
- Agent computes Q-values for all possible exercises
- Top-k exercises are returned as recommendations
- Rationale is generated explaining why each exercise is recommended

### 4. **Personalization Factors**
- **User Goals**: Recommendations align with stated fitness goals
- **Fitness Level**: Exercises match current fitness level
- **Injuries**: Contraindicated exercises are filtered out
- **Equipment**: Only exercises with available equipment are recommended
- **Preferences**: User's favorite exercises get boost in ranking
- **Variety**: System encourages trying different exercises
- **Time Constraints**: Workouts fit available time slots

## Extensibility

### Add New Exercises
```python
from exercise_database import Exercise, MuscleGroup, ExerciseDifficulty

new_exercise = Exercise(
    exercise_id="new_exercise",
    name="Exercise Name",
    description="Description",
    primary_muscles={MuscleGroup.CHEST},
    secondary_muscles={MuscleGroup.TRICEPS},
    difficulty=ExerciseDifficulty.INTERMEDIATE,
    duration_minutes=20,
    equipment_required=["equipment"],
    intensity_level=6,
    calories_burned=7,
    contraindications=[]
)

db.add_exercise(new_exercise)
```

### Add New User Goals
```python
class UserGoal(Enum):
    YOUR_GOAL = "your_goal"
```

### Customize Reward Function
Edit `_calculate_reward()` method in `ExerciseRecommendationEnv` to adjust weights for different factors.

## Performance Metrics

The system tracks:
- **Episode Rewards**: Total reward per training episode
- **Training Loss**: DQN loss convergence
- **User Satisfaction**: Average feedback scores
- **Recommendation Quality**: Goal alignment and safety compliance

## Future Enhancements

1. **Multi-user Collaboration**: Learn from aggregated user feedback
2. **Real-time Adaptation**: Quickly adapt to user's current state
3. **Integration with Wearables**: Use heart rate, step count data
4. **Advanced RL**: Actor-Critic, PPO algorithms
5. **Explainability**: LIME/SHAP for recommendation explanations
6. **A/B Testing**: Compare different recommendation strategies
7. **Federalized Learning**: Train on user devices while preserving privacy

## Requirements

- Python 3.8+
- PyTorch 2.0+
- Gymnasium 0.29+
- Flask 2.0+
- NumPy, Pandas, scikit-learn

## Author

Created as a final year project for personalized fitness recommendations using RL.

## License

MIT License - Feel free to use and modify
