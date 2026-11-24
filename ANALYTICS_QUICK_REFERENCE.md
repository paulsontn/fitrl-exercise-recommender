# Analytics Quick Reference Guide

## Dashboard Navigation

**Access Analytics Tab:**
1. Run: `streamlit run streamlit_dashboard.py`
2. Select **"Analytics"** from sidebar
3. Choose a user from dropdown
4. Navigate through 5 tabs

## What Each Tab Shows

### 📊 Tab 1: Today's Summary
```
Today's Exercises:
- 3 exercises completed
- 50 minutes total
- 260 calories burned
- 7.8/10 average satisfaction

Muscle Groups Worked:
- Glutes (2), Cardio (1), Quadriceps (1)

Exercise List:
- Walking: 30 min, 3/10 intensity, 7.5/10 satisfaction
- Squats: 20 min, 6/10 intensity, 8.0/10 satisfaction
```

### 📈 Tab 2: Weekly Progress (Last 7 Days)
```
Activity Overview:
- 5 days active out of 7 (71% activity rate)
- 15 total exercises
- 300 minutes total
- 1800 calories burned

Trends:
- Daily exercise count chart
- Duration and intensity trends
- Top exercises this week

Most Frequent:
- Walking (5 times)
- Stretching (3 times)
- Yoga (2 times)
```

### 📉 Tab 3: 30-Day Trends
```
Progress Metrics:
- 20 total sessions
- 67% session frequency
- 30 min average per session
- 5.2/10 average intensity

Activity Streaks:
- Current: 4 days
- Personal best: 12 days

Improvement Trends:
- Duration: Improving 📈
- Intensity: Stable →
- Satisfaction: Improving 📈
```

### ✅ Tab 4: Recommendation Analysis
```
RL Agent Performance:
- 25 recommendations generated
- 20 completions
- 80% acceptance rate
- 7.4/10 average satisfaction

Top Recommendations (by rating):
1. Yoga - 8.5/10
2. Squats - 8.0/10
3. Walking - 7.5/10

Health Constraints:
- Injury: lower_back_pain
- Safe exercises completed: 20/20 ✓
```

### 🏆 Tab 5: User Comparison
```
Select 2+ users to compare:

User Rankings (Last 7 Days):
┌─────────────┬──────────┬────────────┬──────────┐
│ User        │ Activity │ Exercises  │ Duration │
├─────────────┼──────────┼────────────┼──────────┤
│ user_001    │ 86%      │ 25         │ 300 min  │
│ user_002    │ 71%      │ 15         │ 180 min  │
│ user_003    │ 43%      │ 8          │ 90 min   │
└─────────────┴──────────┴────────────┴──────────┘

Leaderboards:
- Most Active: user_001 (86%)
- Most Exercises: user_001 (25)
- Longest Duration: user_001 (300 min)
```

## Key Metrics Explained

| Metric | Meaning | Good Value |
|--------|---------|-----------|
| **Activity Rate** | % of days with exercise | 70%+ |
| **Acceptance Rate** | % of recommendations completed | 75%+ |
| **Completion Rate** | Exercises finished / recommended | 100%+ |
| **Satisfaction Score** | User enjoyment (0-10) | 7+/10 |
| **Intensity Level** | Exercise difficulty (1-10) | 5-7 |
| **Current Streak** | Consecutive active days | Growing |
| **Duration Trend** | Is time increasing? | Improving |

## Programmatic Usage

### Get Daily Summary
```python
from exercise_analytics import DailyExerciseAnalytics

analytics = DailyExerciseAnalytics("data")
daily = analytics.get_user_daily_summary("user_001", "2024-12-11")

# Daily totals
print(f"Exercises: {daily['total_exercises']}")
print(f"Duration: {daily['total_duration_minutes']} min")
print(f"Calories: {daily['total_calories_burned']}")
print(f"Satisfaction: {daily['average_satisfaction']}/10")

# Exercise list
for ex in daily['exercises']:
    print(f"{ex['name']}: {ex['duration']} min, "
          f"Intensity {ex['intensity']}/10")
```

### Get Weekly Summary
```python
weekly = analytics.get_weekly_summary("user_001", days_back=7)

print(f"Days Active: {weekly['days_active']}")
print(f"Activity Rate: {weekly['activity_rate']}%")
print(f"Top Exercises: {weekly['most_frequent_exercises']}")
```

### Get Progress Metrics
```python
progress = analytics.get_progress_metrics("user_001", days_back=30)

print(f"Total Sessions: {progress['total_sessions']}")
print(f"Duration Trend: {progress['duration_trend']}")
print(f"Current Streak: {progress['streak_current']} days")
print(f"Longest Streak: {progress['streak_longest']} days")
```

### Analyze Recommendations
```python
rec_analysis = analytics.get_exercise_recommendations_analysis("user_001")

print(f"Acceptance Rate: {rec_analysis['acceptance_rate']:.1f}%")
print(f"Top Rated: {rec_analysis['top_rated_exercises'][0]}")
print(f"Avg Satisfaction: {rec_analysis['average_satisfaction']:.1f}/10")
```

### Compare Users
```python
comparison = analytics.get_comparison_metrics(
    ["user_001", "user_002", "user_003"],
    days_back=7
)

print(f"Most Active: {comparison['rankings']['most_active']}")
print(f"Most Exercises: {comparison['rankings']['most_exercises']}")
```

## Data Flow

```
User Completes Exercise
        ↓
record_completion() called
        ↓
JSON history file updated
        ↓
Analytics reads history
        ↓
Computes metrics on-demand
        ↓
Dashboard displays results
```

## Common Use Cases

### 🎯 **Goal Tracking**
- Check daily summary to confirm you worked out
- Monitor weekly progress for consistency
- Use 30-day trends to see long-term improvement

### 🤖 **RL Agent Evaluation**
- Check recommendation effectiveness tab
- If acceptance rate < 60%, agent needs retraining
- Compare top-rated exercises to your preferences

### 🏥 **Injury Management**
- Verify all completed exercises are safe
- Check injury impact analysis
- Ensure avoided exercises due to constraints

### 🏋️ **Fitness Coaching**
- Compare multiple clients' progress
- Use rankings to motivate less active users
- Monitor each client's satisfaction with recommendations

### 📊 **Personal Analytics**
- Print daily/weekly/monthly reports
- Export metrics for fitness tracking app
- Share progress with trainer

## Tips & Tricks

### 💡 **Maximize Accuracy**
1. Always rate exercises with satisfaction scores (0-10)
2. Record exercise completion immediately after workout
3. Update daily condition fields (fatigue, soreness, sleep) for better recommendations

### 📈 **Improve Trends**
- Current Streak: Exercise every day to build streak
- Duration Trend: Gradually increase workout time
- Satisfaction Trend: Rate exercises honestly for personalization

### 🎯 **RL Agent Tuning**
- Monitor acceptance rate weekly
- If low, retrain agent with more episodes
- Check top-rated exercises to understand your preferences

### 🏆 **Beat the Competition**
- Use comparison metrics to set activity goals
- Track other users' progress for motivation
- Set weekly exercise count targets

## File Locations

- **Analytics Module**: `exercise_analytics.py`
- **Dashboard**: `streamlit_dashboard.py`
- **User Data**: `data/{user_id}_history.json`
- **Demo**: `demo_analytics.py`
- **Full Docs**: `ANALYTICS_DOCUMENTATION.md`
- **Implementation**: `ANALYTICS_IMPLEMENTATION_SUMMARY.md`

## Troubleshooting

### No data showing?
- Register a user first
- Complete some exercises and rate them
- Wait a few minutes for history to update

### Metrics look wrong?
- Check that user_id is correct
- Ensure exercise completions have satisfaction scores
- Verify history file exists in `data/` directory

### Dashboard slow?
- Analytics compute on-demand; typically < 100ms
- For large datasets (1000+ sessions), consider database backend

---

**Version**: 1.0 | **Status**: ✅ Production Ready
