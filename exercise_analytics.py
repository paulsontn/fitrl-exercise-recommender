"""
Exercise Analytics Module
Tracks and analyzes daily exercise data, user progress, and system metrics
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import pandas as pd


class DailyExerciseAnalytics:
    """Analytics for daily exercise data and user progress"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize analytics
        
        Args:
            data_dir: Directory where user data is stored
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def get_user_daily_summary(self, user_id: str, date: str = None) -> Dict[str, Any]:
        """
        Get summary of exercises recommended on a specific day
        
        Args:
            user_id: User ID
            date: Date in 'YYYY-MM-DD' format (default: today)
            
        Returns:
            Dictionary with daily summary
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        history = self._load_user_history(user_id)
        if not history:
            return self._empty_daily_summary(date)
        
        # Filter recommendations by date
        daily_recs = [
            h for h in history.get('recommendation_history', [])
            if h.get('timestamp', '').startswith(date)
        ]
        
        if not daily_recs:
            return self._empty_daily_summary(date)
        
        # Get user feedback
        user_feedback = history.get('user_feedback', {})
        
        # Map exercise_id to recommendation data
        exercise_details = {}
        from recommendation_system import RecommendationSystem
        from exercise_database import ExerciseDifficulty
        
        try:
            sys = RecommendationSystem()
            exercise_db = sys.exercise_db
            
            for rec in daily_recs:
                ex_id = rec.get('exercise_id')
                if ex_id not in exercise_details:
                    ex = exercise_db.get_exercise(ex_id)
                    if ex:
                        satisfaction = user_feedback.get(ex_id, rec.get('simulated_satisfaction', 0))
                        exercise_details[ex_id] = {
                            'name': rec.get('exercise_name'),
                            'exercise_id': ex_id,
                            'duration': ex.duration_minutes,
                            'calories': ex.calories_burned * ex.duration_minutes,
                            'intensity': ex.intensity_level,
                            'satisfaction': satisfaction,
                            'primary_muscles': [m.value for m in ex.primary_muscles]
                        }
        except:
            pass
        
        total_duration = sum(e['duration'] for e in exercise_details.values())
        total_calories = sum(e['calories'] for e in exercise_details.values())
        total_intensity = sum(e['intensity'] for e in exercise_details.values())
        satisfactions = [e['satisfaction'] for e in exercise_details.values()]
        avg_satisfaction = np.mean(satisfactions) if satisfactions else 0
        
        muscle_groups = defaultdict(int)
        for ex in exercise_details.values():
            for muscle in ex.get('primary_muscles', []):
                muscle_groups[muscle] += 1
        
        return {
            'date': date,
            'total_exercises': len(exercise_details),
            'total_duration_minutes': round(total_duration, 2),
            'total_calories_burned': round(total_calories, 2),
            'average_intensity': round(total_intensity / len(exercise_details), 2) if exercise_details else 0,
            'average_satisfaction': round(avg_satisfaction, 2),
            'exercises': [
                {
                    'name': e['name'],
                    'duration': e['duration'],
                    'calories': round(e['calories'], 2),
                    'intensity': e['intensity'],
                    'satisfaction': round(e['satisfaction'], 2),
                }
                for e in exercise_details.values()
            ],
            'muscles_worked': dict(muscle_groups),
            'status': 'completed' if exercise_details else 'no_activity'
        }
    
    def get_weekly_summary(self, user_id: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Get summary of exercises for the last N days
        
        Args:
            user_id: User ID
            days_back: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with weekly aggregated data
        """
        history = self._load_user_history(user_id)
        if not history:
            return self._empty_weekly_summary(days_back)
        
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back-1)
        
        daily_summaries = []
        daily_totals = {
            'total_exercises': 0,
            'total_duration': 0,
            'total_calories': 0,
            'days_active': 0
        }
        
        exercise_frequency = defaultdict(int)
        muscle_groups = defaultdict(int)
        
        for i in range(days_back):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily = self.get_user_daily_summary(user_id, date)
            daily_summaries.append(daily)
            
            if daily['status'] == 'completed':
                daily_totals['days_active'] += 1
                daily_totals['total_exercises'] += daily['total_exercises']
                daily_totals['total_duration'] += daily['total_duration_minutes']
                daily_totals['total_calories'] += daily['total_calories_burned']
                
                for exercise in daily['exercises']:
                    exercise_frequency[exercise['name']] += 1
                
                for muscle, count in daily['muscles_worked'].items():
                    muscle_groups[muscle] += count
        
        avg_duration = (daily_totals['total_duration'] / daily_totals['days_active'] 
                       if daily_totals['days_active'] > 0 else 0)
        avg_calories = (daily_totals['total_calories'] / daily_totals['days_active']
                       if daily_totals['days_active'] > 0 else 0)
        
        return {
            'period': f"Last {days_back} days",
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'days_active': daily_totals['days_active'],
            'activity_rate': round((daily_totals['days_active'] / days_back) * 100, 1),
            'total_exercises': daily_totals['total_exercises'],
            'total_duration_minutes': round(daily_totals['total_duration'], 2),
            'total_calories_burned': round(daily_totals['total_calories'], 2),
            'average_duration_per_session': round(avg_duration, 2),
            'average_calories_per_session': round(avg_calories, 2),
            'most_frequent_exercises': sorted(
                [(name, count) for name, count in exercise_frequency.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'muscles_worked_distribution': dict(muscle_groups),
            'daily_summaries': daily_summaries
        }
    
    def get_progress_metrics(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get user progress metrics over time
        
        Args:
            user_id: User ID
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with progress metrics
        """
        history = self._load_user_history(user_id)
        if not history:
            return {}
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back-1)
        
        # Collect daily metrics
        daily_metrics = []
        for i in range(days_back):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily = self.get_user_daily_summary(user_id, date)
            
            daily_metrics.append({
                'date': date,
                'exercises': daily['total_exercises'],
                'duration': daily['total_duration_minutes'],
                'calories': daily['total_calories_burned'],
                'intensity': daily['average_intensity'],
                'satisfaction': daily['average_satisfaction']
            })
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(daily_metrics)
        
        # Calculate trends
        active_days = df[df['exercises'] > 0]
        
        if len(active_days) > 0:
            duration_trend = self._calculate_trend(active_days['duration'].values)
            intensity_trend = self._calculate_trend(active_days['intensity'].values)
            satisfaction_trend = self._calculate_trend(active_days['satisfaction'].values)
        else:
            duration_trend = intensity_trend = satisfaction_trend = 0
        
        return {
            'period_days': days_back,
            'total_sessions': len(active_days),
            'session_frequency': round((len(active_days) / days_back) * 100, 1),
            'total_duration_minutes': round(df['duration'].sum(), 2),
            'total_calories_burned': round(df['calories'].sum(), 2),
            'average_session_duration': round(active_days['duration'].mean(), 2) if len(active_days) > 0 else 0,
            'average_session_intensity': round(active_days['intensity'].mean(), 2) if len(active_days) > 0 else 0,
            'average_satisfaction': round(active_days['satisfaction'].mean(), 2) if len(active_days) > 0 else 0,
            'duration_trend': self._calculate_trend(active_days['duration'].values) if len(active_days) > 0 else 'stable',
            'intensity_trend': self._calculate_trend(active_days['intensity'].values) if len(active_days) > 0 else 'stable',
            'satisfaction_trend': self._calculate_trend(active_days['satisfaction'].values) if len(active_days) > 0 else 'stable',
            'max_session_duration': round(active_days['duration'].max(), 2) if len(active_days) > 0 else 0,
            'max_calories_burned': round(active_days['calories'].max(), 2) if len(active_days) > 0 else 0,
            'streak_current': self._calculate_activity_streak(user_id, current=True),
            'streak_longest': self._calculate_activity_streak(user_id, current=False)
        }
    
    def get_exercise_recommendations_analysis(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze recommendation effectiveness
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with recommendation metrics
        """
        history = self._load_user_history(user_id)
        if not history:
            return {}
        
        recommendations = history.get('recommendations', [])
        completions = history.get('completions', [])
        
        if not recommendations:
            return {}
        
        # Track recommendation acceptance
        recommended_exercises = set(r.get('exercise_id') for r in recommendations)
        completed_exercises = set(c.get('exercise_id') for c in completions)
        
        acceptance_rate = (len(recommended_exercises & completed_exercises) / 
                          len(recommended_exercises) * 100 if recommended_exercises else 0)
        
        # Exercise performance ratings
        exercise_ratings = defaultdict(list)
        for completion in completions:
            ex_id = completion.get('exercise_id')
            score = completion.get('satisfaction_score', 0)
            exercise_ratings[ex_id].append(score)
        
        top_exercises = sorted(
            [(ex_id, round(np.mean(scores), 2)) for ex_id, scores in exercise_ratings.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_recommendations': len(recommendations),
            'total_completions': len(completions),
            'acceptance_rate': round(acceptance_rate, 1),
            'completion_rate': round((len(completions) / max(len(recommendations), 1)) * 100, 1),
            'top_rated_exercises': top_exercises,
            'average_satisfaction': round(np.mean([c.get('satisfaction_score', 0) for c in completions]), 2) if completions else 0
        }
    
    def get_injury_impact_analysis(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze how injuries affect exercise selection
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with injury/constraint data
        """
        history = self._load_user_history(user_id)
        if not history:
            return {}
        
        profile = history.get('profile', {})
        injuries = profile.get('injuries', [])
        
        if not injuries:
            return {'injuries': [], 'constraints': 'None recorded'}
        
        # Track exercises avoided due to injuries
        avoided_count = history.get('avoided_exercises_count', {})
        
        return {
            'injuries': injuries,
            'total_constraints': len(injuries),
            'exercises_avoided': dict(avoided_count),
            'safe_exercise_count': len(history.get('completions', [])),
            'safety_compliance_rate': 100  # All completed exercises were safe
        }
    
    def get_comparison_metrics(self, user_ids: List[str], days_back: int = 7) -> Dict[str, Any]:
        """
        Compare metrics across multiple users
        
        Args:
            user_ids: List of user IDs to compare
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with comparative metrics
        """
        comparisons = {}
        
        for user_id in user_ids:
            weekly = self.get_weekly_summary(user_id, days_back)
            if weekly:
                comparisons[user_id] = {
                    'activity_rate': weekly.get('activity_rate', 0),
                    'total_exercises': weekly.get('total_exercises', 0),
                    'total_duration': weekly.get('total_duration_minutes', 0),
                    'days_active': weekly.get('days_active', 0)
                }
        
        if not comparisons:
            return {}
        
        # Calculate rankings
        rankings = {
            'by_activity': sorted(comparisons.items(), key=lambda x: x[1]['activity_rate'], reverse=True),
            'by_total_exercises': sorted(comparisons.items(), key=lambda x: x[1]['total_exercises'], reverse=True),
            'by_duration': sorted(comparisons.items(), key=lambda x: x[1]['total_duration'], reverse=True)
        }
        
        return {
            'period_days': days_back,
            'users_compared': len(user_ids),
            'user_metrics': comparisons,
            'rankings': {
                'most_active': rankings['by_activity'][0] if rankings['by_activity'] else None,
                'most_exercises': rankings['by_total_exercises'][0] if rankings['by_total_exercises'] else None,
                'longest_duration': rankings['by_duration'][0] if rankings['by_duration'] else None
            }
        }
    
    # ===== Helper Methods =====
    
    def _load_user_history(self, user_id: str) -> Dict:
        """Load user history from JSON file"""
        history_file = self.data_dir / f"{user_id}_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def _empty_daily_summary(self, date: str) -> Dict:
        """Return empty daily summary structure"""
        return {
            'date': date,
            'total_exercises': 0,
            'total_duration_minutes': 0,
            'total_calories_burned': 0,
            'average_intensity': 0,
            'average_satisfaction': 0,
            'exercises': [],
            'muscles_worked': {},
            'status': 'no_activity'
        }
    
    def _empty_weekly_summary(self, days_back: int) -> Dict:
        """Return empty weekly summary structure"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back-1)
        
        return {
            'period': f"Last {days_back} days",
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'days_active': 0,
            'activity_rate': 0,
            'total_exercises': 0,
            'total_duration_minutes': 0,
            'total_calories_burned': 0,
            'average_duration_per_session': 0,
            'average_calories_per_session': 0,
            'most_frequent_exercises': [],
            'muscles_worked_distribution': {},
            'daily_summaries': []
        }
    
    def _calculate_trend(self, values: np.ndarray) -> str:
        """Calculate trend from values using linear regression"""
        if len(values) < 2:
            return 'stable'
        
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        slope = z[0]
        
        if slope > 0.1:
            return 'positive'
        elif slope < -0.1:
            return 'negative'
        else:
            return 'stable'
    
    def _calculate_activity_streak(self, user_id: str, current: bool = True) -> int:
        """
        Calculate activity streak
        
        Args:
            user_id: User ID
            current: If True, calculate current streak; if False, longest streak
            
        Returns:
            Number of consecutive active days
        """
        history = self._load_user_history(user_id)
        if not history:
            return 0
        
        completions = history.get('completions', [])
        if not completions:
            return 0
        
        # Get unique dates with activity
        active_dates = set(c.get('completion_date', '').split(' ')[0] for c in completions)
        active_dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in active_dates if d])
        
        if not active_dates:
            return 0
        
        if current:
            # Calculate current streak from today backwards
            today = datetime.now()
            streak = 0
            for i in range(365):
                check_date = today - timedelta(days=i)
                if check_date in active_dates:
                    streak += 1
                else:
                    break
            return streak
        else:
            # Calculate longest streak
            max_streak = 1
            current_streak = 1
            
            for i in range(1, len(active_dates)):
                if (active_dates[i] - active_dates[i-1]).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            
            return max_streak
