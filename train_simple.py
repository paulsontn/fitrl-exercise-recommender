"""
Simple Training Script - Better for Admin Dashboard Monitoring
Minimal output that shows real-time progress clearly
"""

import sys
import argparse
import numpy as np
from user_profile import UserProfile, FitnessLevel, UserGoal
from exercise_database import ExerciseDatabase
from exercise_env import ExerciseRecommendationEnv
from rl_agent import DQNAgent
from trainer import ExerciseRecommendationTrainer


def main():
    parser = argparse.ArgumentParser(description="Train the RL agent")
    parser.add_argument("--num_episodes", type=int, default=100, help="Number of episodes to train")
    args = parser.parse_args()
    
    print("[START] Training initialization...")
    print(f"[CONFIG] Episodes: {args.num_episodes}")
    print()
    
    # Create training user profile
    user_profile = UserProfile(
        user_id="training_user",
        age=30,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
        available_time=45,
        injuries=[],
        equipment_access=["dumbbells", "barbell", "bench", "pull_up_bar"],
        preferred_exercises=["bench_press", "squats", "pull_ups"]
    )
    
    # Initialize components
    print("[LOAD] Loading exercise database...")
    exercise_db = ExerciseDatabase()
    exercises_count = len(exercise_db.get_all_exercises())
    print(f"[LOAD] Loaded {exercises_count} exercises")
    
    print("[INIT] Creating environment...")
    env = ExerciseRecommendationEnv(user_profile, exercise_db)
    print(f"[INIT] Environment ready (action_space: {len(env.suitable_exercises)} exercises)")
    
    print("[INIT] Initializing DQN agent...")
    agent = DQNAgent(
        state_size=15,
        action_size=len(env.suitable_exercises),
        learning_rate=0.001,
        gamma=0.99
    )
    print("[INIT] Agent initialized")
    print()
    
    # Train
    print(f"[TRAIN] Starting {args.num_episodes} episodes...")
    print("=" * 60)
    
    trainer = ExerciseRecommendationTrainer(agent, env)
    rewards, lengths = trainer.train(num_episodes=args.num_episodes, update_frequency=4)
    
    print("=" * 60)
    print()
    
    # Save model
    print("[SAVE] Saving trained model...")
    agent.save("trained_agent.pt")
    print("[SAVE] Model saved to trained_agent.pt")
    print()
    
    # Final stats
    avg_reward = np.mean(rewards[-10:])
    print("[STATS] Training Summary:")
    print(f"  - Total Episodes: {args.num_episodes}")
    print(f"  - Average Reward (last 10): {avg_reward:.2f}")
    print(f"  - Best Episode Reward: {max(rewards):.2f}")
    print(f"  - Worst Episode Reward: {min(rewards):.2f}")
    print()
    
    print("[COMPLETE] Training finished successfully!")
    print("[READY] Model is ready for use in the dashboard")


if __name__ == "__main__":
    main()
