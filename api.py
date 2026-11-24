"""
Flask API for Exercise Recommendation System
Provides REST endpoints for the recommendation engine
"""

from flask import Flask, request, jsonify
from typing import Dict, Any
import logging
from user_profile import UserProfile, FitnessLevel, UserGoal
from recommendation_system import RecommendationSystem

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize recommendation system
try:
    recommendation_system = RecommendationSystem(agent_path="trained_agent.pt")
except Exception as e:
    print(f"Warning: Could not load trained agent: {e}")
    recommendation_system = RecommendationSystem()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Exercise Recommendation System'}), 200


@app.route('/api/users/register', methods=['POST'])
def register_user():
    """
    Register a new user
    
    Request body:
    {
        "user_id": "user_001",
        "age": 30,
        "fitness_level": "INTERMEDIATE",
        "goals": ["muscle_gain", "weight_loss"],
        "available_time": 45,
        "injuries": [],
        "equipment_access": ["dumbbells", "barbell"],
        "preferred_exercises": ["bench_press", "squats"]
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        required = ['user_id', 'age', 'fitness_level', 'goals']
        if not all(field in data for field in required):
            return jsonify({'error': f'Missing required fields: {required}'}), 400
        
        # Parse fitness level
        fitness_level = FitnessLevel[data['fitness_level'].upper()]
        
        # Parse goals
        goals = [UserGoal(goal) for goal in data.get('goals', [])]
        
        # Create user profile
        user_profile = UserProfile(
            user_id=data['user_id'],
            age=data['age'],
            fitness_level=fitness_level,
            goals=goals if goals else [UserGoal.GENERAL_FITNESS],
            available_time=data.get('available_time', 30),
            injuries=data.get('injuries', []),
            equipment_access=data.get('equipment_access', []),
            preferred_exercises=data.get('preferred_exercises', [])
        )
        
        # Register user
        recommender = recommendation_system.register_user(user_profile)
        
        return jsonify({
            'status': 'success',
            'message': f'User {user_profile.user_id} registered',
            'user_id': user_profile.user_id
        }), 201
    
    except KeyError as e:
        return jsonify({'error': f'Invalid value: {str(e)}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id: str):
    """
    Get exercise recommendations for a user
    
    Query parameters:
    - num_recommendations: Number of recommendations (default: 5)
    - exploration: Whether to use exploration (default: false)
    """
    try:
        # Get recommender
        recommender = recommendation_system.get_recommender(user_id)
        
        # Get parameters
        num_recs = request.args.get('num_recommendations', 5, type=int)
        exploration = request.args.get('exploration', 'false').lower() == 'true'
        
        # Get recommendations
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
    """
    Get a personalized workout plan
    
    Query parameters:
    - duration: Session duration in minutes (default: 45)
    """
    try:
        # Get recommender
        recommender = recommendation_system.get_recommender(user_id)
        
        # Get parameters
        duration = request.args.get('duration', 45, type=int)
        
        # Generate workout
        workout = recommender.recommend_personalized_workout(session_duration=duration)
        
        return jsonify(workout), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error generating workout: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/feedback/<user_id>', methods=['POST'])
def submit_feedback(user_id: str):
    """
    Submit feedback on a recommendation
    
    Request body:
    {
        "exercise_id": "bench_press",
        "satisfaction_score": 8.5
    }
    """
    try:
        data = request.json
        
        if 'exercise_id' not in data or 'satisfaction_score' not in data:
            return jsonify({'error': 'Missing exercise_id or satisfaction_score'}), 400
        
        exercise_id = data['exercise_id']
        score = float(data['satisfaction_score'])
        
        # Get recommender
        recommender = recommendation_system.get_recommender(user_id)
        
        # Record feedback
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


@app.route('/api/complete/<user_id>', methods=['POST'])
def complete_exercise(user_id: str):
    """
    Record that a user completed an exercise. Request body:
    {
      "exercise_id": "bench_press",
      "satisfaction_score": 8.5   # optional
    }
    """
    try:
        data = request.json
        if 'exercise_id' not in data:
            return jsonify({'error': 'Missing exercise_id'}), 400

        exercise_id = data['exercise_id']
        satisfaction = data.get('satisfaction_score', None)
        if satisfaction is not None:
            satisfaction = float(satisfaction)

        recommender = recommendation_system.get_recommender(user_id)
        entry = recommender.record_completion(exercise_id, satisfaction_score=satisfaction)

        return jsonify({'status': 'success', 'entry': entry}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error recording completion: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_profile(user_id: str):
    """Get user profile information"""
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
            'preferred_exercises': profile.preferred_exercises
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/exercises', methods=['GET'])
def list_exercises():
    """List all available exercises"""
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
                'equipment_required': ex.equipment_required,
                'primary_muscles': [m.value for m in ex.primary_muscles]
            })
        
        return jsonify({
            'total': len(exercise_list),
            'exercises': exercise_list
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing exercises: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("Starting Exercise Recommendation API Server...")
    print("Available endpoints:")
    print("  POST   /api/users/register - Register a new user")
    print("  GET    /api/users/<user_id> - Get user profile")
    print("  GET    /api/recommendations/<user_id> - Get recommendations")
    print("  GET    /api/workout/<user_id> - Get personalized workout")
    print("  POST   /api/feedback/<user_id> - Submit user feedback")
    print("  GET    /api/exercises - List all exercises")
    print("\nServer running on http://localhost:5000")
    
    # Disable Flask auto-reloader to avoid repeated process restarts in development
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
