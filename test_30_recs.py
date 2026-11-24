"""
Test requesting 30 recommendations for a registered user
"""
from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal

sys = RecommendationSystem(agent_path="trained_agent.pt")
user = UserProfile(
    user_id="test_30",
    age=35,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.GENERAL_FITNESS],
    available_time=30,
    injuries=[],
    equipment_access=["dumbbells"],
    preferred_exercises=[]
)
rec = sys.register_user(user)
recs = rec.get_recommendations(num_recommendations=30, use_exploration=False)
print(f"Requested 30, received {len(recs)} recommendations")
for i, r in enumerate(recs[:30]):
    print(i+1, r['exercise_id'], r.get('rationale',''))
