"""
Test recording a completion via the new API and local method
"""
import requests
from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal

# Local test (direct call)
sys = RecommendationSystem(agent_path="trained_agent.pt")
user = UserProfile(
    user_id="complete_test",
    age=40,
    fitness_level=FitnessLevel.INTERMEDIATE,
    goals=[UserGoal.GENERAL_FITNESS],
    available_time=30,
    injuries=[],
    equipment_access=["dumbbells"],
    preferred_exercises=[],
    fatigue=2.0,
    soreness=1.0,
    sleep_hours=7.0,
    resting_heart_rate=60
)
rec = sys.register_user(user)
recs = rec.get_recommendations(num_recommendations=5)
print('Got recommendations:', [r['exercise_id'] for r in recs])
entry = rec.record_completion(recs[0]['exercise_id'], satisfaction_score=8.0)
print('Recorded entry:', entry)

# If API server is running, test HTTP endpoint (uncomment to use)
# payload = { 'exercise_id': recs[0]['exercise_id'], 'satisfaction_score': 8.0 }
# r = requests.post('http://127.0.0.1:5000/api/complete/complete_test', json=payload)
# print('API response:', r.json())
