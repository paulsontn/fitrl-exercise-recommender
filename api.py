"""
Flask REST API for Exercise Recommendation System
Provides CORS-enabled endpoints for user registration, recommendations,
personalized workouts, feedback, completions, and analytics.
"""
import os
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from user_profile import UserProfile, FitnessLevel, UserGoal
from recommendation_system import RecommendationSystem
from exercise_analytics_v2 import ExerciseAnalytics

# Initialize Flask app
BASE_DIR = Path(__file__).parent
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize recommendation system & analytics
try:
    recommendation_system = RecommendationSystem(
        agent_path=str(BASE_DIR / "trained_agent.pt"),
        data_dir=str(BASE_DIR / "data")
    )
except Exception as e:
    logger.warning(f"Could not load trained agent: {e}")
    recommendation_system = RecommendationSystem(data_dir=str(BASE_DIR / "data"))

analytics_engine = ExerciseAnalytics(str(BASE_DIR / "data"), system=recommendation_system)


@app.after_request
def add_cors_headers(response):
    """Enable Cross-Origin Resource Sharing so web_demo.html works from any origin."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response


@app.route('/', methods=['GET'])
def serve_web_demo():
    """Serve web_demo.html directly at root URL."""
    if (BASE_DIR / "web_demo.html").exists():
        return send_from_directory(BASE_DIR, "web_demo.html")
    return jsonify({'status': 'running', 'docs': '/health'}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Exercise Recommendation System',
        'registered_users': len(recommendation_system.user_manager.profiles),
        'total_exercises': len(recommendation_system.exercise_db.get_all_exercises())
    }), 200


@app.route('/api/users', methods=['GET'])
def list_users():
    """List all registered user IDs and summary profiles."""
    users = []
    for uid, p in recommendation_system.user_manager.profiles.items():
        users.append({
            'user_id': uid,
            'age': p.age,
            'fitness_level': p.fitness_level.name,
            'available_time': p.available_time,
            'goals': [g.value for g in p.goals]
        })
    return jsonify({'users': users, 'count': len(users)}), 200


@app.route('/api/users/register', methods=['POST', 'OPTIONS'])
def register_user():
    """Register or update a user profile."""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Request body must be valid JSON'}), 400

        required = ['user_id', 'age', 'fitness_level']
        missing = [field for field in required if not data.get(field) and data.get(field) != 0]
        if missing:
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

        user_id = str(data['user_id']).strip()
        if not user_id:
            return jsonify({'error': 'user_id cannot be empty'}), 400

        age = int(data['age'])
        if not (13 <= age <= 110):
            return jsonify({'error': 'Age must be between 13 and 110'}), 400

        fitness_level = FitnessLevel[str(data['fitness_level']).upper()]

        raw_goals = data.get('goals', [])
        goals = []
        for g in raw_goals:
            try:
                goals.append(UserGoal(g))
            except ValueError:
                pass

        user_profile = UserProfile(
            user_id=user_id,
            age=age,
            fitness_level=fitness_level,
            goals=goals if goals else [UserGoal.GENERAL_FITNESS],
            available_time=max(5, min(240, int(data.get('available_time', 30)))),
            injuries=[str(i).strip() for i in data.get('injuries', []) if str(i).strip()],
            equipment_access=[str(e).strip().lower() for e in data.get('equipment_access', []) if str(e).strip()],
            preferred_exercises=[str(p).strip() for p in data.get('preferred_exercises', []) if str(p).strip()],
            fatigue=float(data.get('fatigue', 0.0)),
            soreness=float(data.get('soreness', 0.0)),
            sleep_hours=float(data.get('sleep_hours', 8.0)),
            resting_heart_rate=int(data.get('resting_heart_rate', 60))
        )

        recommender = recommendation_system.register_user(user_profile)

        return jsonify({
            'status': 'success',
            'message': f'User {user_profile.user_id} registered',
            'user_id': user_profile.user_id,
            'suitable_exercises_count': len(recommender.suitable_exercises)
        }), 201

    except KeyError as e:
        return jsonify({'error': f'Invalid fitness level: {str(e)}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id: str):
    """Get exercise recommendations for a user."""
    try:
        recommender = recommendation_system.get_recommender(user_id)
        num_recs = max(1, min(30, request.args.get('num_recommendations', 5, type=int)))
        exploration = request.args.get('exploration', 'false').lower() == 'true'

        recommendations = recommender.get_recommendations(
            num_recommendations=num_recs,
            use_exploration=exploration
        )

        return jsonify({
            'user_id': user_id,
            'recommendations': recommendations,
            'count': len(recommendations)
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/workout/<user_id>', methods=['GET'])
def get_personalized_workout(user_id: str):
    """Get a personalized timed workout plan."""
    try:
        recommender = recommendation_system.get_recommender(user_id)
        duration = max(5, min(240, request.args.get('duration', 45, type=int)))
        workout = recommender.recommend_personalized_workout(session_duration=duration)
        return jsonify(workout), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error generating workout: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/feedback/<user_id>', methods=['POST', 'OPTIONS'])
def submit_feedback(user_id: str):
    """Submit satisfaction feedback on a recommended exercise."""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json(silent=True)
        if not data or 'exercise_id' not in data or 'satisfaction_score' not in data:
            return jsonify({'error': 'Missing exercise_id or satisfaction_score'}), 400

        exercise_id = str(data['exercise_id'])
        score = float(data['satisfaction_score'])

        recommender = recommendation_system.get_recommender(user_id)
        recommender.provide_feedback(exercise_id, score)

        return jsonify({
            'status': 'success',
            'message': 'Feedback recorded',
            'user_id': user_id,
            'exercise_id': exercise_id,
            'satisfaction_score': score
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/complete/<user_id>', methods=['POST', 'OPTIONS'])
def complete_exercise(user_id: str):
    """Record that a user completed an exercise and compute RL reward."""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json(silent=True)
        if not data or 'exercise_id' not in data:
            return jsonify({'error': 'Missing exercise_id'}), 400

        exercise_id = str(data['exercise_id'])
        satisfaction = data.get('satisfaction_score', None)
@app.route('/api/users/<user_id>', methods=['GET', 'DELETE', 'OPTIONS'])
def get_or_delete_user_profile(user_id: str):
    """Get full user profile details or permanently delete a user."""
    if request.method == 'OPTIONS':
        return '', 204

    if request.method == 'DELETE':
        try:
            recommendation_system.delete_user(user_id, delete_history=True)
            return jsonify({
                'status': 'success',
                'message': f'User {user_id} deleted'
            }), 200
        except ValueError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    try:
        profile = recommendation_system.get_user_profile(user_id)
        return jsonify({
            'user_id': profile.user_id,
            'age': profile.age,
            'fitness_level': profile.fitness_level.name,
            'goals': [g.value for g in profile.goals],
            'available_time': profile.available_time,
            'injuries': profile.injuries,
            'equipment_access': profile.equipment_access,
            'preferred_exercises': profile.preferred_exercises,
            'fatigue': getattr(profile, 'fatigue', 0.0),
            'soreness': getattr(profile, 'soreness', 0.0),
            'sleep_hours': getattr(profile, 'sleep_hours', 8.0),
            'resting_heart_rate': getattr(profile, 'resting_heart_rate', 60)
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/analytics/<user_id>', methods=['GET'])
def get_user_analytics(user_id: str):
    """Get daily, weekly, and effectiveness analytics for a user."""
    try:
        recommendation_system.get_user_profile(user_id)
        daily = analytics_engine.get_user_daily_summary(user_id)
        weekly = analytics_engine.get_weekly_summary(user_id, days_back=7)
        effectiveness = analytics_engine.get_exercise_recommendations_analysis(user_id)
        return jsonify({
            'user_id': user_id,
            'daily': daily,
            'weekly': weekly,
            'effectiveness': effectiveness
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/exercises', methods=['GET'])
def list_exercises():
    """List all available exercises in the database."""
    try:
        exercises = recommendation_system.exercise_db.get_all_exercises()
        exercise_list = []
        for ex in exercises:
            exercise_list.append({
                'exercise_id': ex.exercise_id,
                'name': ex.name,
                'description': ex.description,
                'difficulty': ex.difficulty.name,
                'duration_minutes': ex.duration_minutes,
                'intensity_level': ex.intensity_level,
                'calories_burned': ex.calories_burned,
                'sets': ex.sets,
                'reps': ex.reps,
                'equipment_required': ex.equipment_required,
                'contraindications': ex.contraindications,
                'primary_muscles': [m.value for m in ex.primary_muscles]
            })

        return jsonify({
            'total': len(exercise_list),
            'exercises': exercise_list
        }), 200

    except Exception as e:
        logger.error(f"Error listing exercises: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/exercises/analyze', methods=['GET'])
def analyze_known_exercise():
    """Analyze any known exercise (from DB or custom home routine) for calories, intensity, and target muscles."""
    query = request.args.get('name', '').strip().lower()
    duration = max(1, min(240, request.args.get('duration', 15, type=int)))
    if not query:
        return jsonify({'error': 'Please enter an exercise name'}), 400

    # 1. Check main ExerciseDatabase first
    for ex in recommendation_system.exercise_db.get_all_exercises():
        if query in ex.name.lower() or query in ex.exercise_id.lower():
            return jsonify({
                'name': ex.name,
                'source': 'RL Exercise Database',
                'intensity_level': ex.intensity_level,
                'calories_per_min': ex.calories_burned,
                'estimated_calories': round(ex.calories_burned * duration, 1),
                'duration_minutes': duration,
                'primary_muscles': [m.value.replace('_', ' ').title() for m in ex.primary_muscles],
                'equipment_required': ex.equipment_required or ['Bodyweight'],
                'contraindications': [c.replace('_', ' ') for c in ex.contraindications],
                'description': ex.description
            }), 200

    # 2. Check custom home routine & common bodyweight movements
    known_home_movements = {
        'jumping jack': {'name': 'Jumping Jacks', 'intensity': 7, 'kcal_min': 9.0, 'muscles': ['Cardio', 'Calves', 'Shoulders', 'Core', 'Full Body'], 'eq': ['Bodyweight'], 'desc': 'Classic full-body aerobic warm-up and fat-burning movement elevating heart rate quickly.'},
        'mountain climber': {'name': 'Mountain Climbers', 'intensity': 8, 'kcal_min': 10.0, 'muscles': ['Core', 'Abs', 'Shoulders', 'Hip Flexors', 'Cardio'], 'eq': ['Bodyweight'], 'desc': 'Dynamic plank-position cardio exercise targeting lower abs and cardiovascular stamina.'},
        'fast walk': {'name': 'Fast Brisk Walking', 'intensity': 5, 'kcal_min': 5.5, 'muscles': ['Cardio', 'Quadriceps', 'Calves', 'Glutes'], 'eq': ['Bodyweight'], 'desc': 'Brisk pace walking to burn belly fat steadily with low joint impact.'},
        'walking': {'name': 'Brisk Walking', 'intensity': 4, 'kcal_min': 4.8, 'muscles': ['Cardio', 'Legs', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Steady-state aerobic walking ideal for daily fat loss and active recovery.'},
        'running': {'name': 'Outdoor / Treadmill Running', 'intensity': 8, 'kcal_min': 11.0, 'muscles': ['Cardio', 'Quadriceps', 'Hamstrings', 'Calves', 'Core'], 'eq': ['Bodyweight or Treadmill'], 'desc': 'Sustained aerobic endurance exercise strengthening heart, lungs, and lower body.'},
        'jogging': {'name': 'Steady Jogging', 'intensity': 6, 'kcal_min': 8.5, 'muscles': ['Cardio', 'Legs', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Moderate conversational-pace aerobic run building stamina and calorie expenditure.'},
        'cycling': {'name': 'Cycling / Stationary Bike', 'intensity': 6, 'kcal_min': 8.0, 'muscles': ['Quadriceps', 'Hamstrings', 'Calves', 'Cardio'], 'eq': ['Bicycle or Stationary Bike'], 'desc': 'Low-impact leg endurance and cardiovascular conditioning workout.'},
        'skipping': {'name': 'Skipping Rope (Jump Rope)', 'intensity': 8, 'kcal_min': 12.0, 'muscles': ['Cardio', 'Calves', 'Shoulders', 'Core'], 'eq': ['Jump Rope'], 'desc': 'High-intensity cardio conditioning that rapidly burns calories and improves footwork.'},
        'jump rope': {'name': 'Skipping Rope (Jump Rope)', 'intensity': 8, 'kcal_min': 12.0, 'muscles': ['Cardio', 'Calves', 'Shoulders', 'Core'], 'eq': ['Jump Rope'], 'desc': 'High-intensity cardio conditioning that rapidly burns calories and improves footwork.'},
        'stair': {'name': 'Stair Climbing', 'intensity': 7, 'kcal_min': 9.5, 'muscles': ['Quadriceps', 'Glutes', 'Calves', 'Cardio'], 'eq': ['Stairs'], 'desc': 'Vertical lower-body cardio workout that elevates heart rate and builds leg stamina.'},
        'lunge': {'name': 'Walking / Reverse Lunges', 'intensity': 6, 'kcal_min': 7.2, 'muscles': ['Quadriceps', 'Glutes', 'Hamstrings', 'Core'], 'eq': ['Bodyweight or Dumbbells'], 'desc': 'Unilateral leg exercise strengthening thighs, glutes, and single-leg balance.'},
        'calf raise': {'name': 'Standing Calf Raises', 'intensity': 3, 'kcal_min': 3.8, 'muscles': ['Calves', 'Ankle Stabilizers'], 'eq': ['Bodyweight or Step'], 'desc': 'Lower-leg isolation movement strengthening calf muscles and ankle resilience.'},
        'dip': {'name': 'Chair / Parallel Bar Dips', 'intensity': 7, 'kcal_min': 7.2, 'muscles': ['Triceps', 'Lower Chest', 'Front Shoulders'], 'eq': ['Chair or Dip Bars'], 'desc': 'Compound upper-body pushing movement targeting triceps and chest.'},
        'bicep curl': {'name': 'Dumbbell / Backpack Bicep Curls', 'intensity': 4, 'kcal_min': 4.5, 'muscles': ['Biceps', 'Forearms'], 'eq': ['Dumbbells or Backpack'], 'desc': 'Arm isolation exercise building bicep peak and elbow flexion strength.'},
        'crunch': {'name': 'Abdominal / Bicycle Crunches', 'intensity': 5, 'kcal_min': 5.5, 'muscles': ['Abs', 'Obliques', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Targeted abdominal flexion exercise sculpting upper, lower, and side abs.'},
        'situp': {'name': 'Sit-ups', 'intensity': 5, 'kcal_min': 5.8, 'muscles': ['Abs', 'Hip Flexors', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Classic trunk-flexion core endurance exercise.'},
        'leg raise': {'name': 'Lying Leg Raises', 'intensity': 5, 'kcal_min': 5.0, 'muscles': ['Lower Abs', 'Hip Flexors', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Controlled lower-abdominal exercise targeting lower belly musculature.'},
        'bicycle crunch': {'name': 'Bicycle Crunches', 'intensity': 6, 'kcal_min': 6.5, 'muscles': ['Obliques', 'Rectus Abdominis', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Rotational core movement engaging both upper/lower abs and side obliques.'},
        'heel touch': {'name': 'Alternating Heel Touches', 'intensity': 4, 'kcal_min': 4.5, 'muscles': ['Obliques', 'Core'], 'eq': ['Bodyweight'], 'desc': 'Side-to-side core crunch targeting oblique waist definition.'},
        'incline pushup': {'name': 'Incline Pushups', 'intensity': 5, 'kcal_min': 6.0, 'muscles': ['Chest', 'Shoulders', 'Triceps'], 'eq': ['Elevated Surface / Chair'], 'desc': 'Beginner-friendly chest and upper-body push movement reducing shoulder strain.'},
        'backpack row': {'name': 'Backpack Bent-Over Rows', 'intensity': 6, 'kcal_min': 6.5, 'muscles': ['Upper Back', 'Lats', 'Biceps', 'Posture'], 'eq': ['Loaded Backpack'], 'desc': 'Pulling strength exercise correcting rounded shoulders and building back thickness.'},
        'pike pushup': {'name': 'Pike Pushups', 'intensity': 7, 'kcal_min': 7.5, 'muscles': ['Shoulders', 'Upper Chest', 'Triceps'], 'eq': ['Bodyweight'], 'desc': 'Bodyweight overhead pressing variation targeting deltoids and upper body.'},
        'glute bridge': {'name': 'Glute Bridges', 'intensity': 4, 'kcal_min': 4.8, 'muscles': ['Glutes', 'Hamstrings', 'Lower Back'], 'eq': ['Bodyweight'], 'desc': 'Hip-extension movement strengthening glutes and supporting lower-back posture.'},
        'shadow boxing': {'name': 'Shadow Boxing', 'intensity': 7, 'kcal_min': 8.5, 'muscles': ['Cardio', 'Shoulders', 'Core', 'Back'], 'eq': ['Bodyweight'], 'desc': 'Dynamic upper-body and core cardio conditioning with zero equipment.'},
        'reverse lunge': {'name': 'Reverse Lunges', 'intensity': 6, 'kcal_min': 7.0, 'muscles': ['Quadriceps', 'Glutes', 'Hamstrings'], 'eq': ['Bodyweight'], 'desc': 'Knee-friendly unilateral leg movement improving balance and lower-body strength.'},
        'backpack shoulder press': {'name': 'Backpack Shoulder Press', 'intensity': 6, 'kcal_min': 6.5, 'muscles': ['Shoulders', 'Triceps', 'Upper Core'], 'eq': ['Loaded Backpack'], 'desc': 'Overhead pressing movement using a weighted backpack for home muscle building.'},
        'high knees': {'name': 'High Knees', 'intensity': 8, 'kcal_min': 10.5, 'muscles': ['Cardio', 'Core', 'Hip Flexors', 'Calves'], 'eq': ['Bodyweight'], 'desc': 'Explosive HIIT cardio drill maximizing heart rate and fat oxidation.'},
        'squat jump': {'name': 'Squat Jumps', 'intensity': 9, 'kcal_min': 11.5, 'muscles': ['Quadriceps', 'Glutes', 'Calves', 'Cardio'], 'eq': ['Bodyweight'], 'desc': 'Plyometric lower-body power exercise for intense calorie expenditure.'},
        'yoga': {'name': 'Yoga & Full-Body Stretching', 'intensity': 3, 'kcal_min': 3.5, 'muscles': ['Full Body', 'Spine', 'Hips', 'Hamstrings', 'Shoulders'], 'eq': ['Yoga Mat or Carpet'], 'desc': 'Restorative mobility and flexibility practice reducing stiffness and stress.'},
        'stretch': {'name': 'Full-Body Stretching & Mobility', 'intensity': 3, 'kcal_min': 3.2, 'muscles': ['Full Body', 'Joints', 'Hamstrings', 'Hips'], 'eq': ['Bodyweight'], 'desc': 'Gentle static and dynamic stretching improving joint range of motion.'},
        'mobility': {'name': 'Joint Mobility & Dynamic Flow', 'intensity': 3, 'kcal_min': 3.5, 'muscles': ['Full Body', 'Hips', 'Thoracic Spine', 'Shoulders'], 'eq': ['Bodyweight'], 'desc': 'Restorative joint range-of-motion flow reducing stiffness and improving posture.'}
    }

    normalized_q = query.rstrip('s')
    for key, info in known_home_movements.items():
        if key in query or key in normalized_q or normalized_q in key or query in info['name'].lower():
            return jsonify({
                'name': info['name'],
                'source': 'Home Fitness Knowledge Base',
                'intensity_level': info['intensity'],
                'calories_per_min': info['kcal_min'],
                'estimated_calories': round(info['kcal_min'] * duration, 1),
                'duration_minutes': duration,
                'primary_muscles': info['muscles'],
                'equipment_required': info['eq'],
                'contraindications': ['Consult a physician if experiencing acute joint pain'],
                'description': info['desc']
            }), 200

    return jsonify({'error': f'Exercise "{query}" not found. Try searching e.g. Squats, Pushups, Plank, Fast Walk, Skipping Rope, Backpack Rows, Burpees.'}), 404


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Exercise Recommendation API Server on http://0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)