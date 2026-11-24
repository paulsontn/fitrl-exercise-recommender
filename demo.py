"""
Simple Demo Script - Quick Test Without Training
Shows the system in action with minimal setup
"""

from user_profile import UserProfile, FitnessLevel, UserGoal
from exercise_database import ExerciseDatabase
from recommendation_system import RecommendationSystem
import json


def print_header(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_exercise_detail(rec):
    """Print detailed exercise recommendation"""
    print(f"\n  ★ {rec['rank']}. {rec['exercise_name'].upper()}")
    print(f"     Duration: {rec['duration_minutes']} minutes | Intensity: {rec['intensity_level']}/10")
    print(f"     Calories burned: {rec['calories_burned']:.1f}/min")
    print(f"     Primary targets: {', '.join(rec['primary_muscles'][:2])}")
    if rec['equipment_required']:
        print(f"     Equipment needed: {', '.join(rec['equipment_required'])}")
    print(f"     💡 {rec['rationale']}")


def demo_basic_recommendations():
    """Demo 1: Basic recommendation"""
    print_header("DEMO 1: BASIC PERSONALIZED RECOMMENDATIONS")
    
    # Create recommendation system (uses untrained agent for demo)
    system = RecommendationSystem()
    
    # Create a sample user
    john = UserProfile(
        user_id="john_athlete",
        age=28,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
        available_time=45,
        injuries=[],
        equipment_access=["dumbbells", "barbell", "bench", "pull_up_bar"],
        preferred_exercises=["bench_press", "squats", "pull_ups"]
    )
    
    print(f"\nUser Profile:")
    print(f"  ID: {john.user_id}")
    print(f"  Age: {john.age} years")
    print(f"  Fitness Level: {john.fitness_level.name}")
    print(f"  Goals: {', '.join([g.value for g in john.goals])}")
    print(f"  Available Time: {john.available_time} minutes")
    print(f"  Equipment: {', '.join(john.equipment_access)}")
    print(f"  Preferred Exercises: {', '.join(john.preferred_exercises)}")
    
    # Register and get recommendations
    recommender = system.register_user(john)
    print(f"\n✓ User registered successfully!")
    
    print(f"\n📋 Getting personalized recommendations...")
    recommendations = recommender.get_recommendations(num_recommendations=5)
    
    for rec in recommendations:
        print_exercise_detail(rec)
    
    print(f"\n✓ Recommendations complete!")


def demo_different_fitness_levels():
    """Demo 2: Different fitness levels"""
    print_header("DEMO 2: RECOMMENDATIONS FOR DIFFERENT FITNESS LEVELS")
    
    system = RecommendationSystem()
    
    # Create three users with different fitness levels
    users = [
        UserProfile(
            user_id="alice_beginner",
            age=32,
            fitness_level=FitnessLevel.BEGINNER,
            goals=[UserGoal.GENERAL_FITNESS, UserGoal.WEIGHT_LOSS],
            available_time=30,
            injuries=[],
            equipment_access=[],
            preferred_exercises=[]
        ),
        UserProfile(
            user_id="bob_intermediate",
            age=26,
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=[UserGoal.MUSCLE_GAIN],
            available_time=45,
            injuries=[],
            equipment_access=["dumbbells", "barbell"],
            preferred_exercises=[]
        ),
        UserProfile(
            user_id="carol_advanced",
            age=24,
            fitness_level=FitnessLevel.ADVANCED,
            goals=[UserGoal.MUSCLE_GAIN],
            available_time=60,
            injuries=[],
            equipment_access=["dumbbells", "barbell", "bench", "pull_up_bar"],
            preferred_exercises=["deadlifts", "bench_press"]
        )
    ]
    
    for user in users:
        print(f"\n{'─'*80}")
        print(f"User: {user.user_id} ({user.fitness_level.name})")
        print(f"Goal: {user.goals[0].value}")
        
        recommender = system.register_user(user)
        recommendations = recommender.get_recommendations(num_recommendations=3)
        
        for rec in recommendations:
            print(f"\n  • {rec['exercise_name']} (Intensity: {rec['intensity_level']}/10)")
            print(f"    {rec['rationale']}")


def demo_injury_constraints():
    """Demo 3: Handling injuries"""
    print_header("DEMO 3: EXERCISE RECOMMENDATIONS WITH INJURY CONSTRAINTS")
    
    system = RecommendationSystem()
    
    print("\nExample User with Lower Back Pain:")
    user = UserProfile(
        user_id="dave_injured",
        age=35,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.WEIGHT_LOSS, UserGoal.MUSCLE_GAIN],
        available_time=45,
        injuries=["lower_back_pain"],
        equipment_access=["dumbbells"],
        preferred_exercises=[]
    )
    
    print(f"  Injuries: {', '.join(user.injuries)}")
    print(f"  Note: Exercises like deadlifts and heavy squats are avoided")
    
    recommender = system.register_user(user)
    recommendations = recommender.get_recommendations(num_recommendations=5)
    
    print(f"\n✓ Recommended exercises (safe for lower back):")
    for rec in recommendations:
        print(f"  • {rec['exercise_name']}")
    
    # Verify no dangerous exercises
    db = ExerciseDatabase()
    for rec in recommendations:
        exercise = db.get_exercise(rec['exercise_id'])
        is_safe = exercise.is_suitable_for(user.injuries)
        status = "✓ Safe" if is_safe else "✗ UNSAFE"
        print(f"    {rec['exercise_name']}: {status}")


def demo_personalized_workout():
    """Demo 4: Full workout planning"""
    print_header("DEMO 4: PERSONALIZED WORKOUT PLAN GENERATION")
    
    system = RecommendationSystem()
    
    user = UserProfile(
        user_id="emma_workout",
        age=27,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN],
        available_time=60,
        injuries=[],
        equipment_access=["dumbbells", "barbell", "bench"],
        preferred_exercises=[]
    )
    
    print(f"\nUser: {user.user_id}")
    print(f"Available Time: {user.available_time} minutes")
    print(f"Fitness Level: {user.fitness_level.name}")
    
    recommender = system.register_user(user)
    
    # Generate workout plans of different durations
    for duration in [30, 45, 60]:
        print(f"\n{'─'*40}")
        print(f"Workout Plan ({duration} minutes):")
        print('─'*40)
        
        workout = recommender.recommend_personalized_workout(session_duration=duration)
        
        print(f"Number of exercises: {len(workout['exercises'])}")
        print(f"Estimated calories: {workout['estimated_calories']:.0f}")
        print(f"Goals targeted: {', '.join(workout['goals_targeted'])}")
        
        total_time = 0
        for i, ex in enumerate(workout['exercises'], 1):
            exercise = system.exercise_db.get_exercise(ex['exercise_id'])
            total_time += exercise.duration_minutes
            print(f"  {i}. {ex['exercise_name']} ({ex['duration_minutes']} min)")
        
        print(f"Total: {total_time} minutes")


def demo_exercise_database():
    """Demo 5: Exercise database exploration"""
    print_header("DEMO 5: EXERCISE DATABASE EXPLORATION")
    
    db = ExerciseDatabase()
    exercises = db.get_all_exercises()
    
    print(f"\nTotal Exercises: {len(exercises)}")
    
    # Count by difficulty
    from exercise_database import ExerciseDifficulty
    print(f"\nBy Difficulty Level:")
    for difficulty in ExerciseDifficulty:
        count = len(db.filter_by_difficulty(difficulty))
        print(f"  • {difficulty.name}: {count} exercises")
    
    # Sample exercises
    print(f"\nSample Exercises:")
    for i, exercise in enumerate(exercises[:6], 1):
        print(f"\n  {i}. {exercise.name}")
        print(f"     Difficulty: {exercise.difficulty.name}")
        print(f"     Duration: {exercise.duration_minutes} min")
        print(f"     Intensity: {exercise.intensity_level}/10")
        print(f"     Calories: {exercise.calories_burned:.1f}/min")
        print(f"     Targets: {', '.join([m.value for m in list(exercise.primary_muscles)[:2]])}")


def demo_feedback_system():
    """Demo 6: User feedback"""
    print_header("DEMO 6: USER FEEDBACK AND LEARNING")
    
    system = RecommendationSystem()
    
    user = UserProfile(
        user_id="frank_feedback",
        age=30,
        fitness_level=FitnessLevel.INTERMEDIATE,
        goals=[UserGoal.MUSCLE_GAIN],
        available_time=45,
        injuries=[],
        equipment_access=["dumbbells", "barbell"],
        preferred_exercises=[]
    )
    
    recommender = system.register_user(user)
    
    print("\n1️⃣  Initial Recommendations:")
    recs1 = recommender.get_recommendations(num_recommendations=3)
    for rec in recs1:
        print(f"  • {rec['exercise_name']}")
    
    print("\n2️⃣  User Provides Feedback:")
    feedback_data = {
        recs1[0]['exercise_id']: 9.0,  # Loved it
        recs1[1]['exercise_id']: 6.0,  # Okay
        recs1[2]['exercise_id']: 4.0,  # Didn't like
    }
    
    for exercise_id, score in feedback_data.items():
        recommender.provide_feedback(exercise_id, score)
        db = ExerciseDatabase()
        exercise_name = db.get_exercise(exercise_id).name
        print(f"  {exercise_name}: {score}/10")
    
    print("\n3️⃣  System Adapts (learned user preferences)")
    print("  Note: In production, agent would retrain on feedback")
    print("  This example shows feedback storage mechanism")


def main():
    """Run all demos"""
    print("\n" + "█"*80)
    print("█  RL-BASED EXERCISE RECOMMENDATION SYSTEM - DEMO")
    print("█"*80)
    print("""
This demo shows the system's capabilities without requiring training.
The system can still make good recommendations using the trained agent
or default behavior.
    """)
    
    try:
        # Run all demos
        demo_exercise_database()
        demo_basic_recommendations()
        demo_different_fitness_levels()
        demo_injury_constraints()
        demo_personalized_workout()
        demo_feedback_system()
        
        # Final summary
        print_header("DEMO COMPLETE ✓")
        print("""
The system is working! Next steps:

1. **Train the Agent** (optional):
   python main.py

2. **Start the API Server**:
   python api.py
   Then access: http://localhost:5000

3. **Run Full Evaluation**:
   python evaluation.py

4. **Read Documentation**:
   - README.md - Project overview
   - QUICKSTART.md - Quick start guide
   - ARCHITECTURE.md - System design
   - PROJECT_SUMMARY.md - Complete summary
        """)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
