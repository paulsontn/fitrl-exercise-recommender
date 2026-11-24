#!/usr/bin/env python3
"""
Test script for metrics functionality
"""

import sys
import os
sys.path.append('.')

from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal

def test_metrics_functionality():
    """Test the metrics functionality with sample data"""
    print("Testing metrics functionality...")

    # Create recommendation system
    sys = RecommendationSystem(agent_path="trained_agent.pt")

    # Register test users
    print("Registering test users...")
    user1 = UserProfile(
        user_id="test_user_1",
        age=25,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN],
        available_time=30,
        injuries=[],
        equipment_access=["dumbbells", "barbell"],
        preferred_exercises=["bench_press", "squats"],
        fatigue=2.0,
        soreness=1.0,
        sleep_hours=7.0,
        resting_heart_rate=65
    )

    user2 = UserProfile(
        user_id="test_user_2",
        age=30,
        fitness_level=FitnessLevel.BEGINNER,
        goals=[UserGoal.GENERAL_FITNESS],
        available_time=45,
        injuries=[],
        equipment_access=["dumbbells", "mat"],
        preferred_exercises=["push_ups", "planks"],
        fatigue=1.0,
        soreness=0.5,
        sleep_hours=8.0,
        resting_heart_rate=60
    )

    sys.register_user(user1)
    sys.register_user(user2)

    # Get recommenders
    rec1 = sys.get_recommender("test_user_1")
    rec2 = sys.get_recommender("test_user_2")

    # Simulate some recommendations and feedback
    print("Simulating recommendations and feedback...")

    # Add some recommendation history for user 1
    rec1.recommendation_history = [
        {
            'exercise_id': 'bench_press',
            'exercise_name': 'Bench Press',
            'duration_minutes': 10,
            'intensity_level': 7,
            'completed': True,
            'satisfaction': 8.5
        },
        {
            'exercise_id': 'squats',
            'exercise_name': 'Squats',
            'duration_minutes': 15,
            'intensity_level': 8,
            'completed': False,
            'satisfaction': None
        }
    ]

    # Add explicit feedback for user 1
    rec1.user_feedback = {
        'bench_press': 9.0,
        'squats': 7.5
    }

    # Add some recommendation history for user 2
    rec2.recommendation_history = [
        {
            'exercise_id': 'push_ups',
            'exercise_name': 'Push Ups',
            'duration_minutes': 8,
            'intensity_level': 6,
            'completed': True,
            'satisfaction': 8.0
        }
    ]

    # Add explicit feedback for user 2
    rec2.user_feedback = {
        'push_ups': 8.5,
        'planks': 9.0
    }

    # Test metrics calculation
    print("\nTesting metrics calculation...")

    total_recommendations = sum(len(rec.recommendation_history) for rec in sys.recommenders.values())
    print(f"Total recommendations: {total_recommendations}")

    # Test feedback aggregation
    total_feedbacks = 0
    feedback_data = []

    for uid, rec in sys.recommenders.items():
        # Count feedback from user_feedback dict
        total_feedbacks += len(rec.user_feedback)
        for ex_id, score in rec.user_feedback.items():
            feedback_data.append({'Exercise': ex_id, 'Score': score, 'User': uid})

        # Count feedback from recommendation_history (completed exercises with satisfaction)
        for entry in rec.recommendation_history:
            if 'completed' in entry and entry['completed'] and 'satisfaction' in entry and entry['satisfaction'] is not None:
                total_feedbacks += 1
                feedback_data.append({
                    'Exercise': entry.get('exercise_id', entry.get('exercise_name', 'Unknown')),
                    'Score': entry['satisfaction'],
                    'User': uid
                })

    print(f"Total feedbacks: {total_feedbacks}")
    print(f"Feedback data count: {len(feedback_data)}")

    acceptance_rate = (total_feedbacks / total_recommendations * 100) if total_recommendations > 0 else 0
    print(f"Engagement rate: {acceptance_rate:.1f}%")

    # Show feedback data
    print("\nFeedback data:")
    for item in feedback_data:
        print(f"  {item}")

    print("\nTest completed successfully!")
    return True

if __name__ == "__main__":
    test_metrics_functionality()
