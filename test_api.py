import requests
import json

BASE_URL = "http://localhost:5000"

def test_api():
    print("🧪 Testing RL Exercise Recommendation API")
    print("=" * 50)

    # Test 1: List exercises
    print("\n1. Testing GET /api/exercises")
    try:
        response = requests.get(f"{BASE_URL}/api/exercises")
        if response.status_code == 200:
            exercises = response.json()
            print(f"✅ Success: {len(exercises['exercises'])} exercises loaded")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Register user
    print("\n2. Testing POST /api/users/register")
    user_data = {
        "user_id": "test_user",
        "age": 30,
        "fitness_level": "INTERMEDIATE",
        "goals": ["muscle_gain", "weight_loss"],
        "available_time": 45,
        "injuries": [],
        "equipment_access": ["dumbbells", "barbell"]
    }
    try:
        response = requests.post(f"{BASE_URL}/api/users/register",
                               json=user_data,
                               headers={"Content-Type": "application/json"})
        if response.status_code == 201:
            print("✅ Success: User registered")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Get recommendations
    print("\n3. Testing GET /api/recommendations/test_user")
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/test_user?num_recommendations=3")
        if response.status_code == 200:
            recs = response.json()
            print("✅ Success: Recommendations generated")
            for i, rec in enumerate(recs['recommendations'][:3], 1):
                print(f"   {i}. {rec['exercise_name']} ({rec['duration_minutes']} min)")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Get workout plan
    print("\n4. Testing GET /api/workout/test_user")
    try:
        response = requests.get(f"{BASE_URL}/api/workout/test_user?duration=45")
        if response.status_code == 200:
            workout = response.json()
            print("✅ Success: Workout plan generated")
            print(f"   Duration: {workout['total_duration']} min")
            print(f"   Exercises: {len(workout['exercises'])}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n🎉 API Testing Complete!")

if __name__ == "__main__":
    test_api()
