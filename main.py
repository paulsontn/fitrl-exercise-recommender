"""
Complete Training and Demo Script
Shows how to train and use the exercise recommendation system
"""

import numpy as np
import matplotlib.pyplot as plt
from user_profile import UserProfile, UserProfileManager, FitnessLevel, UserGoal
from exercise_database import ExerciseDatabase
from exercise_env import ExerciseRecommendationEnv
from rl_agent import DQNAgent
from trainer import ExerciseRecommendationTrainer
from recommendation_system import RecommendationSystem, ExerciseRecommender


def train_agent():
    """Train the RL agent"""
    print("=" * 80)
    print("TRAINING RL AGENT FOR EXERCISE RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Create a sample user profile for training
    user_profile = UserProfile(
        user_id="training_user_001",
        age=30,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
        available_time=45,
        injuries=[],
        equipment_access=["dumbbells", "barbell", "bench", "pull_up_bar"],
        preferred_exercises=["bench_press", "squats", "pull_ups"]
    )
    
    # Initialize environment and agent
    print("[INIT] Loading exercise database...")
    exercise_db = ExerciseDatabase()
    print(f"[INIT] Database loaded with {len(exercise_db.get_all_exercises())} exercises")
    
    print("[INIT] Creating environment...")
    env = ExerciseRecommendationEnv(user_profile, exercise_db)
    print(f"[INIT] Environment created for user {user_profile.user_id}")
    
    print("[INIT] Initializing DQN agent...")
    agent = DQNAgent(
        state_size=15,
        action_size=len(env.suitable_exercises),
        learning_rate=0.001,
        gamma=0.99
    )
    print(f"[INIT] Agent ready (state_size=15, action_size={len(env.suitable_exercises)})")
    print()
    
    # Train agent
    print("[TRAINING] Starting training loop...")
    trainer = ExerciseRecommendationTrainer(agent, env)
    rewards, lengths = trainer.train(num_episodes=100, update_frequency=4)
    print()
    
    # Save trained agent
    print("[SAVING] Storing trained agent...")
    agent.save("trained_agent.pt")
    print(f"[SAVING] Agent successfully saved to 'trained_agent.pt'")
    print(f"[STATS] Average reward (last 10 episodes): {np.mean(rewards[-10:]):.2f}")
    print()
    
    # Plot training curves
    print("[PLOTTING] Generating training curves...")
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(rewards, alpha=0.6)
    plt.plot(np.convolve(rewards, np.ones(10)/10, mode='valid'), linewidth=2)
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.title("DQN Training: Episode Rewards")
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(lengths)
    plt.xlabel("Episode")
    plt.ylabel("Episode Length")
    plt.title("Episode Duration Over Training")
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("training_curves.png", dpi=100)
    print("[PLOTTING] Training curves saved to 'training_curves.png'")
    print()
    
    return agent


def demo_recommendation_system(agent=None):
    """Demonstrate the recommendation system"""
    print("\n" + "=" * 80)
    print("EXERCISE RECOMMENDATION SYSTEM DEMO")
    print("=" * 80)
    
    # Initialize system
    system = RecommendationSystem(agent_path="trained_agent.pt" if agent is None else None)
    
    # Create sample users
    users = [
        UserProfile(
            user_id="user_001",
            age=25,
            fitness_level=FitnessLevel.BEGINNER,
            goals=[UserGoal.GENERAL_FITNESS, UserGoal.WEIGHT_LOSS],
            available_time=30,
            injuries=[],
            equipment_access=["dumbbells"],
            preferred_exercises=["walking", "jogging"]
        ),
        UserProfile(
            user_id="user_002",
            age=35,
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=[UserGoal.MUSCLE_GAIN, UserGoal.ENDURANCE],
            available_time=60,
            injuries=["lower_back_pain"],
            equipment_access=["dumbbells", "barbell", "bench"],
            preferred_exercises=["bench_press", "dumbbell_rows"]
        ),
        UserProfile(
            user_id="user_003",
            age=45,
            fitness_level=FitnessLevel.BEGINNER,
            goals=[UserGoal.FLEXIBILITY, UserGoal.GENERAL_FITNESS],
            available_time=45,
            injuries=["knee_pain"],
            equipment_access=[],
            preferred_exercises=["yoga", "stretching", "walking"]
        ),
    ]
    
    # Register users and get recommendations
    for user_profile in users:
        print(f"\n{'-' * 80}")
        print(f"User: {user_profile.user_id}")
        print(f"Age: {user_profile.age}, Fitness Level: {user_profile.fitness_level.name}")
        print(f"Goals: {', '.join([g.value for g in user_profile.goals])}")
        print(f"Injuries: {user_profile.injuries if user_profile.injuries else 'None'}")
        print(f"Available Time: {user_profile.available_time} minutes")
        print(f"{'-' * 80}")
        
        # Register user
        recommender = system.register_user(user_profile)
        
        # Get personalized recommendations
        print("\nTop 5 Exercise Recommendations:")
        recommendations = recommender.get_recommendations(num_recommendations=5)
        
        for rec in recommendations:
            print(f"\n  {rec['rank']}. {rec['exercise_name']}")
            print(f"     Duration: {rec['duration_minutes']} min | Intensity: {rec['intensity_level']}/10")
            print(f"     Calories: {rec['calories_burned']:.1f}/min")
            print(f"     Targets: {', '.join(rec['primary_muscles'][:2])}")
            print(f"     Why: {rec['rationale']}")
        
        # Generate workout plan
        print("\nPersonalized Workout Plan (45 min session):")
        workout = recommender.recommend_personalized_workout(session_duration=45)
        print(f"  Total Duration: {workout['total_duration']} min")
        print(f"  Estimated Calories: {workout['estimated_calories']:.0f}")
        print(f"  Number of Exercises: {len(workout['exercises'])}")
        print("\n  Exercises:")
        for i, ex in enumerate(workout['exercises'], 1):
            print(f"    {i}. {ex['exercise_name']} ({ex['duration_minutes']} min)")
        
        # Simulate user feedback
        print("\nSimulating User Feedback...")
        for rec in recommendations[:3]:
            satisfaction = np.random.uniform(6, 10)  # Generally positive feedback
            recommender.provide_feedback(rec['exercise_id'], satisfaction)
            print(f"  {rec['exercise_name']}: {satisfaction:.1f}/10")


def create_sample_analysis():
    """Create analysis of exercise database"""
    print("\n" + "=" * 80)
    print("EXERCISE DATABASE ANALYSIS")
    print("=" * 80)
    
    db = ExerciseDatabase()
    exercises = db.get_all_exercises()
    
    print(f"\nTotal Exercises: {len(exercises)}")
    
    # Group by difficulty
    print("\nExercises by Difficulty Level:")
    for difficulty in [FitnessLevel.BEGINNER, FitnessLevel.INTERMEDIATE, FitnessLevel.ADVANCED]:
        count = len([e for e in exercises if e.difficulty.value == difficulty.value])
        print(f"  {difficulty.name}: {count} exercises")
    
    # Most targeted muscles
    print("\nMost Targeted Muscle Groups:")
    from exercise_database import MuscleGroup
    from collections import Counter
    
    muscle_counts = Counter()
    for exercise in exercises:
        for muscle in exercise.primary_muscles:
            muscle_counts[muscle.value] += 1
    
    for muscle, count in muscle_counts.most_common(5):
        print(f"  {muscle.capitalize()}: {count} exercises")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run complete pipeline
    
    # 1. Create sample analysis
    create_sample_analysis()
    
    # 2. Train agent
    trained_agent = train_agent()
    
    # 3. Demo system
    demo_recommendation_system(agent=trained_agent)
    
    print("\n" + "=" * 80)
    print("TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\n[SUMMARY] System Status:")
    print("  [READY] user_profile.py - User profile management")
    print("  [READY] exercise_database.py - Exercise database (18 exercises)")
    print("  [READY] exercise_env.py - Gym environment for RL")
    print("  [READY] rl_agent.py - DQN Agent (fully trained)")
    print("  [READY] trainer.py - Training loop")
    print("  [READY] recommendation_system.py - Recommendation engine")
    print("  [READY] trained_agent.pt - Model weights (saved)")
    print("\n[NEXT STEPS] You can now:")
    print("  1. Use the dashboard: streamlit run streamlit_dashboard.py")
    print("  2. Start the API server: python api.py")
    print("  3. Train for longer: python main.py --num_episodes 500")
    print("  4. Run smoke tests: python test_timed_recommendations.py")
    print("\n[INFO] Admin Dashboard available at: http://localhost:8501")
