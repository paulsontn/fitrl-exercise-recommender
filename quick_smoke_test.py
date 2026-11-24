"""
Quick smoke test for RecommendationSystem
Run: python quick_smoke_test.py
"""
import json
from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal


def main():
    print("Instantiating RecommendationSystem...")
    sys = RecommendationSystem(agent_path="trained_agent.pt")

    test_user = UserProfile(
        user_id="smoke_test_user",
        age=28,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.GENERAL_FITNESS],
        available_time=30,
        injuries=[],
        equipment_access=["dumbbells"],
        preferred_exercises=[]
    )

    print("Registering test user...")
    recommender = sys.register_user(test_user)

    print("Requesting recommendations...")
    recs = recommender.get_recommendations(num_recommendations=5, use_exploration=False)

    print(f"Received {len(recs)} recommendations")
    print(json.dumps(recs, indent=2))


if __name__ == '__main__':
    main()
