"""Test timed workout with different available times"""
from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal

# Setup
sys = RecommendationSystem(None)

test_times = [30, 45, 60]

for available_time in test_times:
    user = UserProfile(
        user_id=f'test_user_{available_time}min',
        age=30,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.GENERAL_FITNESS, UserGoal.WEIGHT_LOSS],
        available_time=available_time,
        injuries=[],
        equipment_access=[],
        preferred_exercises=[]
    )
    
    sys.user_manager.create_profile(user)
    sys.register_user(user)
    
    recommender = sys.get_recommender(user.user_id)
    recommendations = recommender.get_recommendations(available_time_minutes=available_time)
    
    total_duration = sum(r['duration_minutes'] for r in recommendations)
    total_calories = sum(r.get('total_calories', 0) for r in recommendations)
    
    print(f"\n⏱️  Available: {available_time} min")
    print(f"   Exercises ({len(recommendations)}):")
    for rec in recommendations:
        print(f"     • {rec['exercise_name']}: {rec['duration_minutes']} min")
    print(f"   Total: {total_duration} min, {total_calories:.0f} cals")
    status = "✅ PERFECT FIT" if total_duration == available_time else "⚠️  LESS THAN"
    print(f"   {status}")
