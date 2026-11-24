from recommendation_system import RecommendationSystem
from user_profile import UserProfile, FitnessLevel, UserGoal
import traceback

print('Instantiating...')
sys = RecommendationSystem(agent_path='trained_agent.pt')
print('Creating user')
user = UserProfile(user_id='smoke', age=28, fitness_level=FitnessLevel.INTERMEDIATE, goals=[UserGoal.GENERAL_FITNESS], available_time=30, injuries=[], equipment_access=['dumbbells'], preferred_exercises=[])
rec = sys.register_user(user)
print('Calling get_recommendations')
try:
    recs = rec.get_recommendations(5)
    print('len:', len(recs))
    print(recs)
except Exception as e:
    traceback.print_exc()
