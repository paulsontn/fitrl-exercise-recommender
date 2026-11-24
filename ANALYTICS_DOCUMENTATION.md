# Exercise Analytics System - Documentation

## Overview

The Exercise Analytics System provides comprehensive tracking and analysis of daily exercise data, user progress metrics, and system performance. It's fully integrated into the Streamlit dashboard under the **Analytics** tab.

## Key Features

### 1. **Daily Summary**
Tracks exercise activity for a specific day:
- Number of exercises completed
- Total duration (minutes)
- Total calories burned
- Average intensity level (1-10 scale)
- Average satisfaction score (0-10 scale)
- Muscle groups worked
- Individual exercise details (duration, intensity, satisfaction)

**Use Case:** Monitor daily workout performance and recovery

### 2. **Weekly Progress**
Aggregates data over the last 7 days:
- Days active / Activity rate (%)
- Total exercises completed
- Total duration and calories
- Average duration & calories per session
- Most frequent exercises
- Daily trend visualization
- Muscle group distribution

**Use Case:** Track weekly consistency and workout patterns

### 3. **30-Day Progress Metrics**
Long-term progress analysis:
- Total sessions completed
- Session frequency (%)
- Average duration, intensity, and satisfaction
- Activity streaks (current & longest)
- Trend analysis (duration, intensity, satisfaction improving/stable/declining)
- Performance records (max duration, max calories)

**Use Case:** Monitor long-term progress and identify trends

### 4. **Recommendation Effectiveness**
Evaluates how well the RL agent's recommendations match user preferences:
- Total recommendations generated
- Total completions
- Acceptance rate (%)
- Completion rate (%)
- Top-rated exercises
- Average user satisfaction with recommendations
- Health constraints tracking

**Use Case:** Assess recommendation quality and refine the RL agent

### 5. **User Comparison**
Compare metrics across multiple users:
- Activity rates
- Total exercises
- Duration per user
- Days active
- Rankings by activity, volume, and duration

**Use Case:** Motivate users with friendly competition

## Analytics API

### Core Methods

#### `get_user_daily_summary(user_id, date=None)`
Get daily exercise summary for a specific day.

```python
from exercise_analytics import DailyExerciseAnalytics

analytics = DailyExerciseAnalytics("data")
daily = analytics.get_user_daily_summary("user_001", "2024-12-11")

print(f"Exercises: {daily['total_exercises']}")
print(f"Duration: {daily['total_duration_minutes']} min")
print(f"Calories: {daily['total_calories_burned']}")
print(f"Satisfaction: {daily['average_satisfaction']}/10")
print(f"Muscles: {daily['muscles_worked']}")
```

#### `get_weekly_summary(user_id, days_back=7)`
Get aggregated metrics for the last N days.

```python
weekly = analytics.get_weekly_summary("user_001", days_back=7)

print(f"Days Active: {weekly['days_active']}/7")
print(f"Activity Rate: {weekly['activity_rate']}%")
print(f"Top Exercises: {weekly['most_frequent_exercises']}")
```

#### `get_progress_metrics(user_id, days_back=30)`
Analyze user progress over time with trend detection.

```python
progress = analytics.get_progress_metrics("user_001", days_back=30)

print(f"Sessions: {progress['total_sessions']}")
print(f"Avg Duration: {progress['average_session_duration']} min")
print(f"Duration Trend: {progress['duration_trend']}")  # 'positive', 'negative', 'stable'
print(f"Current Streak: {progress['streak_current']} days")
print(f"Longest Streak: {progress['streak_longest']} days")
```

#### `get_exercise_recommendations_analysis(user_id)`
Evaluate how well recommendations align with user preferences.

```python
rec_analysis = analytics.get_exercise_recommendations_analysis("user_001")

print(f"Acceptance Rate: {rec_analysis['acceptance_rate']:.1f}%")
print(f"Completion Rate: {rec_analysis['completion_rate']:.1f}%")
print(f"Top Rated: {rec_analysis['top_rated_exercises']}")
print(f"Avg Satisfaction: {rec_analysis['average_satisfaction']:.1f}/10")
```

#### `get_injury_impact_analysis(user_id)`
Track how health constraints affect exercise selection.

```python
injury_analysis = analytics.get_injury_impact_analysis("user_001")

print(f"Injuries: {injury_analysis['injuries']}")
print(f"Safe Exercises: {injury_analysis['safe_exercise_count']}")
```

#### `get_comparison_metrics(user_ids, days_back=7)`
Compare multiple users for motivation and competition.

```python
comparison = analytics.get_comparison_metrics(["user_001", "user_002", "user_003"], days_back=7)

print(f"Most Active: {comparison['rankings']['most_active']}")
print(f"Most Exercises: {comparison['rankings']['most_exercises']}")
print(f"Longest Duration: {comparison['rankings']['longest_duration']}")
```

## Data Structure

### User History File (`{user_id}_history.json`)

```json
{
  "profile": {
    "user_id": "user_001",
    "age": 30,
    "fitness_level": "INTERMEDIATE",
    "goals": ["muscle_gain", "weight_loss"],
    "injuries": ["lower_back_pain"]
  },
  "recommendations": [
    {
      "exercise_id": "walking_001",
      "exercise_name": "Walking",
      "timestamp": "2024-12-11T10:00:00"
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
    }
  ]
}
```

## Dashboard Integration

### Analytics Tab Features

**Tab 1: Today's Summary**
- 4 key metrics (exercises, duration, calories, satisfaction)
- Exercise list with details
- Muscle group visualization

**Tab 2: Weekly Progress (Last 7 days)**
- 5 key metrics (days active, activity rate, total exercises, duration, calories)
- Daily trend charts
- Most frequent exercises

**Tab 3: 30-Day Trends**
- 5 key metrics (sessions, frequency, avg duration, avg intensity, avg satisfaction)
- Activity streaks (current & longest)
- Trend analysis (improving/stable/declining)

**Tab 4: Recommendation Analysis**
- 4 key metrics (recommendations, completions, acceptance rate, satisfaction)
- Top-rated exercises chart
- Health constraint tracking

**Tab 5: User Comparison**
- Multi-user selection
- Comparison table (activity rate, exercises, duration, days active)
- Rankings (most active, most exercises, longest duration)

## Trend Analysis

The system automatically detects trends in three metrics:
- **Duration**: Are sessions getting longer or shorter?
- **Intensity**: Is the user pushing harder?
- **Satisfaction**: Is the user enjoying workouts more?

Trend Values:
- `'positive'`: Improving trend (slope > 0.1)
- `'negative'`: Declining trend (slope < -0.1)
- `'stable'`: No significant change

## Activity Streaks

Two types of streaks are tracked:
- **Current Streak**: Consecutive days of activity ending today
- **Longest Streak**: Maximum consecutive active days in history

## Use Cases

### 1. **Personal Fitness Tracking**
Monitor daily, weekly, and monthly progress to stay motivated.

### 2. **Workout Optimization**
Identify which exercises have highest satisfaction scores and plan future workouts accordingly.

### 3. **RL Model Evaluation**
Check recommendation acceptance rate to assess if the RL agent is making good suggestions.

### 4. **Group Fitness Programs**
Compare multiple users to identify high performers and motivate less active users.

### 5. **Injury Management**
Track which exercises are avoided due to injuries and ensure safe activity selection.

### 6. **Trainer Dashboard**
Monitor multiple clients' progress and compliance with workout plans.

## Example Workflow

```python
from exercise_analytics import DailyExerciseAnalytics

# Initialize analytics
analytics = DailyExerciseAnalytics("data")

# 1. Check today's activity
daily = analytics.get_user_daily_summary("user_001")
if daily['total_exercises'] == 0:
    print("No activity today - send reminder")

# 2. Monitor weekly consistency
weekly = analytics.get_weekly_summary("user_001")
if weekly['activity_rate'] < 50:
    print("Low activity rate - suggest more exercises")

# 3. Evaluate long-term progress
progress = analytics.get_progress_metrics("user_001")
if progress['duration_trend'] == 'positive':
    print("Great! You're increasing your workout duration")

# 4. Assess recommendations quality
rec_analysis = analytics.get_exercise_recommendations_analysis("user_001")
if rec_analysis['acceptance_rate'] < 60:
    print("Recommendations need improvement - retrain RL agent")

# 5. Compare with other users
comparison = analytics.get_comparison_metrics(["user_001", "user_002"])
print(f"You rank #{comparison['rankings']['most_active'][1]} by activity")
```

## Performance Notes

- All analytics are computed on-demand from user history files
- For large datasets (1000+ sessions), consider caching or database storage
- Trend analysis requires at least 2 data points
- Streak calculation is exact for current streak, approximated for historical data

## Future Enhancements

- **Predictive Analytics**: Predict future performance based on trends
- **Goal Tracking**: Set fitness goals and monitor progress towards them
- **Smart Recommendations**: Use analytics to improve RL agent training
- **Export Reports**: Generate PDF/HTML reports for users or trainers
- **Real-time Alerts**: Notify users of achievements or compliance issues
- **Database Backend**: Replace JSON files with SQL for better scalability

---

**Created**: December 11, 2024
**Version**: 1.0
**Status**: Production Ready
