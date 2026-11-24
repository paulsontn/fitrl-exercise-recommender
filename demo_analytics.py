"""
Demo: Exercise Analytics System
Shows how to use the analytics module to track and analyze exercise data
"""

from exercise_analytics import DailyExerciseAnalytics
from datetime import datetime
import json
from pathlib import Path


def create_sample_analytics_data():
    """Create sample user data for analytics demo"""
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Sample user history with exercise completions
    sample_history = {
        "profile": {
            "user_id": "demo_user_001",
            "age": 30,
            "fitness_level": "INTERMEDIATE",
            "goals": ["muscle_gain", "weight_loss"],
            "injuries": [],
            "equipment_access": ["dumbbells", "mat"]
        },
        "recommendations": [
            {
                "exercise_id": "walking_001",
                "exercise_name": "Walking",
                "timestamp": "2024-12-11T10:00:00"
            },
            {
                "exercise_id": "squats_003",
                "exercise_name": "Squats",
                "timestamp": "2024-12-11T10:30:00"
            },
            {
                "exercise_id": "pushups_004",
                "exercise_name": "Push-ups",
                "timestamp": "2024-12-10T09:00:00"
            }
        ],
        "completions": [
            {
                "exercise_id": "walking_001",
                "exercise_name": "Walking",
                "duration_minutes": 30,
                "calories_burned": 120,
                "intensity_level": 3,
                "primary_muscles": ["glutes", "cardio"],
                "satisfaction_score": 7.5,
                "completion_date": "2024-12-11 10:30:00"
            },
            {
                "exercise_id": "squats_003",
                "exercise_name": "Squats",
                "duration_minutes": 20,
                "calories_burned": 140,
                "intensity_level": 6,
                "primary_muscles": ["quadriceps", "glutes"],
                "satisfaction_score": 8.0,
                "completion_date": "2024-12-11 11:00:00"
            },
            {
                "exercise_id": "pushups_004",
                "exercise_name": "Push-ups",
                "duration_minutes": 15,
                "calories_burned": 85,
                "intensity_level": 5,
                "primary_muscles": ["chest", "triceps"],
                "satisfaction_score": 7.0,
                "completion_date": "2024-12-10 09:30:00"
            },
            {
                "exercise_id": "yoga_002",
                "exercise_name": "Yoga",
                "duration_minutes": 45,
                "calories_burned": 135,
                "intensity_level": 3,
                "primary_muscles": ["flexibility", "cardio"],
                "satisfaction_score": 8.5,
                "completion_date": "2024-12-09 18:00:00"
            },
            {
                "exercise_id": "running_005",
                "exercise_name": "Running",
                "duration_minutes": 30,
                "calories_burned": 300,
                "intensity_level": 8,
                "primary_muscles": ["cardio", "glutes", "quadriceps"],
                "satisfaction_score": 6.5,
                "completion_date": "2024-12-08 06:30:00"
            }
        ]
    }
    
    # Save sample data
    history_file = data_dir / "demo_user_001_history.json"
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(sample_history, f, indent=2)
    
    print(f"[CREATE] Sample analytics data created in {history_file}")
    return "demo_user_001"


def demo_analytics():
    """Demonstrate analytics functionality"""
    
    print("\n" + "="*80)
    print("EXERCISE ANALYTICS SYSTEM DEMO")
    print("="*80 + "\n")
    
    # Create sample data
    user_id = create_sample_analytics_data()
    
    # Initialize analytics
    analytics = DailyExerciseAnalytics("data")
    
    print("\n" + "-"*80)
    print("1. DAILY SUMMARY (Today)")
    print("-"*80 + "\n")
    
    daily = analytics.get_user_daily_summary(user_id, "2024-12-11")
    print(f"Date: {daily['date']}")
    print(f"Total Exercises: {daily['total_exercises']}")
    print(f"Total Duration: {daily['total_duration_minutes']} minutes")
    print(f"Total Calories: {daily['total_calories_burned']} cal")
    print(f"Average Intensity: {daily['average_intensity']}/10")
    print(f"Average Satisfaction: {daily['average_satisfaction']}/10")
    print(f"\nExercises Completed:")
    for ex in daily['exercises']:
        print(f"  - {ex['name']}: {ex['duration']}min, Intensity: {ex['intensity']}/10, Satisfaction: {ex['satisfaction']}/10")
    print(f"\nMuscles Worked: {dict(daily['muscles_worked'])}")
    
    print("\n" + "-"*80)
    print("2. WEEKLY SUMMARY (Last 7 Days)")
    print("-"*80 + "\n")
    
    weekly = analytics.get_weekly_summary(user_id, days_back=7)
    print(f"Period: {weekly['period']}")
    print(f"Days Active: {weekly['days_active']} out of 7")
    print(f"Activity Rate: {weekly['activity_rate']}%")
    print(f"Total Exercises: {weekly['total_exercises']}")
    print(f"Total Duration: {weekly['total_duration_minutes']} minutes")
    print(f"Total Calories: {weekly['total_calories_burned']} cal")
    print(f"Average Duration per Session: {weekly['average_duration_per_session']} min")
    print(f"Average Calories per Session: {weekly['average_calories_per_session']} cal")
    print(f"\nMost Frequent Exercises:")
    for ex, count in weekly['most_frequent_exercises']:
        print(f"  - {ex}: {count} times")
    
    print("\n" + "-"*80)
    print("3. PROGRESS METRICS (30 Days)")
    print("-"*80 + "\n")
    
    progress = analytics.get_progress_metrics(user_id, days_back=30)
    print(f"Total Sessions: {progress['total_sessions']}")
    print(f"Session Frequency: {progress['session_frequency']}%")
    print(f"Average Session Duration: {progress['average_session_duration']} min")
    print(f"Average Session Intensity: {progress['average_session_intensity']}/10")
    print(f"Average Satisfaction: {progress['average_satisfaction']}/10")
    print(f"\nActivity Streaks:")
    print(f"  Current: {progress['streak_current']} days")
    print(f"  Longest: {progress['streak_longest']} days")
    print(f"\nProgress Trends:")
    trend_map = {'positive': 'Improving', 'negative': 'Declining', 'stable': 'Stable'}
    print(f"  Duration: {trend_map.get(progress['duration_trend'], 'Unknown')}")
    print(f"  Intensity: {trend_map.get(progress['intensity_trend'], 'Unknown')}")
    print(f"  Satisfaction: {trend_map.get(progress['satisfaction_trend'], 'Unknown')}")
    
    print("\n" + "-"*80)
    print("4. RECOMMENDATION EFFECTIVENESS")
    print("-"*80 + "\n")
    
    rec_analysis = analytics.get_exercise_recommendations_analysis(user_id)
    print(f"Total Recommendations: {rec_analysis['total_recommendations']}")
    print(f"Total Completions: {rec_analysis['total_completions']}")
    print(f"Acceptance Rate: {rec_analysis['acceptance_rate']:.1f}%")
    print(f"Completion Rate: {rec_analysis['completion_rate']:.1f}%")
    print(f"Average Satisfaction: {rec_analysis['average_satisfaction']:.1f}/10")
    print(f"\nTop Rated Exercises:")
    for ex_id, rating in rec_analysis['top_rated_exercises']:
        print(f"  - {ex_id}: {rating}/10")
    
    print("\n" + "="*80)
    print("DEMO COMPLETED")
    print("="*80)
    print("\n[INFO] Use the Analytics tab in the Streamlit dashboard to view these metrics")
    print("[INFO] Run: streamlit run streamlit_dashboard.py")


if __name__ == "__main__":
    demo_analytics()
