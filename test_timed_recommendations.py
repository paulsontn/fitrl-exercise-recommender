"""Test timed workout recommendations"""
from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal

# Setup
sys = RecommendationSystem(None)

# Register user with 45 min available time
user = UserProfile(
    user_id='test_user_45min',
    age=30,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.GENERAL_FITNESS, UserGoal.WEIGHT_LOSS],
    available_time=45,  # 45 minutes available
    injuries=[],
    equipment_access=[],
    preferred_exercises=[]
)

sys.user_manager.create_profile(user)
sys.register_user(user)  # Register in system
print(f"✅ Registered user with {user.available_time} minutes available time")

# Get recommendations for the available time
recommender = sys.get_recommender(user.user_id)
recommendations = recommender.get_recommendations(available_time_minutes=45)

print(f"\n📋 Recommendations (should fit in 45 minutes):")
total_duration = 0
total_calories = 0

for rec in recommendations:
    duration = rec['duration_minutes']
    calories = rec.get('total_calories', rec['duration_minutes'] * rec['calories_burned'])
    total_duration += duration
    total_calories += calories
    print(f"  • {rec['exercise_name']}: {duration} min, {calories:.0f} cals")

print(f"\n✅ Total: {total_duration} minutes, {total_calories:.0f} calories")
print(f"   Available: 45 minutes")
print(f"   Status: {'PERFECT FIT' if total_duration <= 45 else 'EXCEEDS TIME'}")
