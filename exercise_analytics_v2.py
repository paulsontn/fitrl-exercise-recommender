"""
Exercise Analytics Module (V2)
Tracks and analyzes exercise data based on actual system data structure
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict


class ExerciseAnalytics:
    """Analytics for exercise recommendations and user progress"""
    
    def __init__(self, data_dir: str = "data", system=None):
        """
        Initialize analytics
        
        Args:
            data_dir: Directory where user data is stored
            system: RecommendationSystem instance for accessing exercise database
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.system = system
    
    def get_user_daily_summary(self, user_id: str, date: str = None) -> Dict[str, Any]:
        """
        Get summary of exercises recommended/tracked on a specific day
        
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
        
        # Group by timestamp to identify sessions
        sessions = {}
        for rec in daily_recs:
            ts = rec.get('timestamp', '')
            if ts:
                # Group by minute (same timestamp = same session)
                session_key = ts[:16]  # YYYY-MM-DDTHH:MM
                if session_key not in sessions:
                    sessions[session_key] = []
                sessions[session_key].append(rec)
        
        # Get user feedback
        user_feedback = history.get('user_feedback', {})
        
        # Process each session
        session_summaries = []
        all_exercises = {}
        
        for session_time, session_recs in sessions.items():
            session_exercises = {}
            
            for rec in session_recs:
                ex_id = rec.get('exercise_id')
                if ex_id not in session_exercises:
                    try:
                        if self.system:
                            ex = self.system.exercise_db.get_exercise(ex_id)
                            if ex:
                                satisfaction = user_feedback.get(ex_id, rec.get('simulated_satisfaction', 0))
                                session_exercises[ex_id] = {
                                    'name': rec.get('exercise_name'),
                                    'exercise_id': ex_id,
                                    'duration': ex.duration_minutes,
                                    'calories': ex.calories_burned * ex.duration_minutes,
                                    'intensity': ex.intensity_level,
                                    'satisfaction': satisfaction,
                                    'primary_muscles': [m.value for m in ex.primary_muscles],
                                    'timestamp': rec.get('timestamp')
                                }
                        else:
                            satisfaction = user_feedback.get(ex_id, rec.get('simulated_satisfaction', 0))
                            session_exercises[ex_id] = {
                                'name': rec.get('exercise_name'),
                                'exercise_id': ex_id,
                                'duration': 30,
                                'calories': 100,
                                'intensity': 5,
                                'satisfaction': satisfaction,
                                'primary_muscles': [],
                                'timestamp': rec.get('timestamp')
                            }
                    except:
                        pass
            
            if session_exercises:
                session_duration = sum(e['duration'] for e in session_exercises.values())
                session_calories = sum(e['calories'] for e in session_exercises.values())
                session_satisfactions = [e['satisfaction'] for e in session_exercises.values()]
                
                # Parse timestamp for time of day
                try:
                    dt = datetime.fromisoformat(session_time.replace('T', ' '))
                    time_of_day = dt.strftime("%I:%M %p")  # 06:30 PM format
                    hour = dt.hour
                except:
                    time_of_day = "Unknown"
                    hour = 12
                
                session_summaries.append({
                    'session_time': session_time,
                    'time_of_day': time_of_day,
                    'hour': hour,
                    'exercise_count': len(session_exercises),
                    'duration_minutes': round(session_duration, 2),
                    'calories_burned': round(session_calories, 2),
                    'avg_satisfaction': round(np.mean(session_satisfactions), 2) if session_satisfactions else 0,
                    'exercises': list(session_exercises.values())
                })
                
                # Add to all exercises
                for ex_id, ex_data in session_exercises.items():
                    if ex_id not in all_exercises:
                        all_exercises[ex_id] = ex_data
        
        # Calculate daily totals
        total_duration = sum(s['duration_minutes'] for s in session_summaries)
        total_calories = sum(s['calories_burned'] for s in session_summaries)
        total_intensity = sum(e['intensity'] for e in all_exercises.values()) / len(all_exercises) if all_exercises else 0
        all_satisfactions = [e['satisfaction'] for e in all_exercises.values()]
        
        # Time distribution analysis
        morning_sessions = [s for s in session_summaries if 6 <= s['hour'] < 12]
        afternoon_sessions = [s for s in session_summaries if 12 <= s['hour'] < 18]
        evening_sessions = [s for s in session_summaries if 18 <= s['hour'] < 24]
        night_sessions = [s for s in session_summaries if s['hour'] < 6]
        
        muscle_groups = defaultdict(int)
        for ex in all_exercises.values():
            for muscle in ex.get('primary_muscles', []):
                muscle_groups[muscle] += 1
        
        return {
            'date': date,
            'total_exercises': len(all_exercises),
            'total_sessions': len(session_summaries),
            'total_duration_minutes': round(total_duration, 2),
            'total_calories_burned': round(total_calories, 2),
            'average_intensity': round(total_intensity, 2),
            'average_satisfaction': round(np.mean(all_satisfactions), 2) if all_satisfactions else 0,
            'sessions': session_summaries,
            'exercises': list(all_exercises.values()),
            'muscles_worked': dict(muscle_groups),
            'time_distribution': {
                'morning': len(morning_sessions),  # 6AM-12PM
                'afternoon': len(afternoon_sessions),  # 12PM-6PM
                'evening': len(evening_sessions),  # 6PM-12AM
                'night': len(night_sessions)  # 12AM-6AM
            },
            'status': 'completed' if all_exercises else 'no_activity'
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
        start_date = end_date - timedelta(days=days_back)
        
        recs = history.get('recommendation_history', [])
        user_feedback = history.get('user_feedback', {})
        
        # Group by date
        daily_data = defaultdict(list)
        for rec in recs:
            ts = rec.get('timestamp', '')
            date = ts.split('T')[0] if 'T' in ts else ts
            
            try:
                rec_date = datetime.strptime(date, "%Y-%m-%d")
                if start_date <= rec_date <= end_date:
                    daily_data[date].append(rec)
            except:
                pass
        
        if not daily_data:
            return self._empty_weekly_summary(days_back)
        
        # Calculate daily summaries
        daily_summaries = []
        total_exercises = 0
        exercise_freq = defaultdict(int)
        
        exercise_db = self.system.exercise_db if self.system else None
        
        for date in sorted(daily_data.keys()):
            recs_today = daily_data[date]
            exercise_set = set()
            total_duration = 0
            total_calories = 0
            satisfactions = []
            
            for rec in recs_today:
                ex_id = rec.get('exercise_id')
                exercise_set.add(ex_id)
                exercise_freq[ex_id] += 1
                
                if exercise_db:
                    try:
                        ex = exercise_db.get_exercise(ex_id)
                        if ex:
                            total_duration += ex.duration_minutes
                            total_calories += ex.calories_burned * ex.duration_minutes
                    except:
                        pass
                
                satisfaction = user_feedback.get(ex_id, rec.get('simulated_satisfaction', 0))
                satisfactions.append(satisfaction)
            
            daily_summaries.append({
                'date': date,
                'total_exercises': len(exercise_set),
                'total_duration_minutes': round(total_duration, 2),
                'total_calories_burned': round(total_calories, 2),
                'average_satisfaction': round(np.mean(satisfactions), 2) if satisfactions else 0
            })
            
            total_exercises += len(exercise_set)
        
        # Most frequent exercises
        most_frequent = sorted(exercise_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        days_active = len(daily_summaries)
        activity_rate = round((days_active / days_back) * 100, 1) if days_back > 0 else 0
        
        total_duration = sum(d['total_duration_minutes'] for d in daily_summaries)
        total_calories = sum(d['total_calories_burned'] for d in daily_summaries)
        
        return {
            'days_active': days_active,
            'activity_rate': activity_rate,
            'total_exercises': total_exercises,
            'total_duration_minutes': round(total_duration, 2),
            'total_calories_burned': round(total_calories, 2),
            'average_duration_per_session': round(total_duration / days_active, 2) if days_active > 0 else 0,
            'most_frequent_exercises': [[ex_id, count] for ex_id, count in most_frequent],
            'daily_summaries': daily_summaries
        }
    
    def get_progress_metrics(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get 30-day progress metrics
        
        Args:
            user_id: User ID
            days_back: Number of days to analyze (default: 30)
            
        Returns:
            Dictionary with progress metrics and trends
        """
        history = self._load_user_history(user_id)
        if not history:
            return {}
        
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        recs = history.get('recommendation_history', [])
        user_feedback = history.get('user_feedback', {})
        
        # Group by date for sessions
        daily_data = defaultdict(list)
        for rec in recs:
            ts = rec.get('timestamp', '')
            date = ts.split('T')[0] if 'T' in ts else ts
            
            try:
                rec_date = datetime.strptime(date, "%Y-%m-%d")
                if start_date <= rec_date <= end_date:
                    daily_data[date].append(rec)
            except:
                pass
        
        if not daily_data:
            return {}
        
        # Calculate metrics
        session_durations = []
        session_intensities = []
        session_satisfactions = []
        active_dates = []
        
        exercise_db = self.system.exercise_db if self.system else None
        
        for date in sorted(daily_data.keys()):
            recs_today = daily_data[date]
            total_duration = 0
            total_intensity = 0
            satisfactions = []
            
            for rec in recs_today:
                ex_id = rec.get('exercise_id')
                
                if exercise_db:
                    try:
                        ex = exercise_db.get_exercise(ex_id)
                        if ex:
                            total_duration += ex.duration_minutes
                            total_intensity += ex.intensity_level
                    except:
                        pass
                
                satisfaction = user_feedback.get(ex_id, rec.get('simulated_satisfaction', 0))
                satisfactions.append(satisfaction)
            
            if total_duration > 0:
                session_durations.append(total_duration)
                session_intensities.append(total_intensity / len(recs_today) if recs_today else 0)
                session_satisfactions.append(np.mean(satisfactions) if satisfactions else 0)
                active_dates.append(datetime.strptime(date, "%Y-%m-%d"))
        
        if not session_durations:
            return {}
        
        # Calculate trends
        if len(session_durations) > 1:
            duration_trend = self._calculate_trend(np.array(session_durations))
            intensity_trend = self._calculate_trend(np.array(session_intensities))
            satisfaction_trend = self._calculate_trend(np.array(session_satisfactions))
        else:
            duration_trend = intensity_trend = satisfaction_trend = 'stable'
        
        # Calculate streaks
        current_streak = self._calculate_streak(active_dates, current=True)
        longest_streak = self._calculate_streak(active_dates, current=False)
        
        return {
            'total_sessions': len(session_durations),
            'session_frequency': round((len(active_dates) / days_back) * 100, 1),
            'average_session_duration': round(np.mean(session_durations), 2),
            'average_session_intensity': round(np.mean(session_intensities), 2),
            'average_satisfaction': round(np.mean(session_satisfactions), 2),
            'streak_current': current_streak,
            'streak_longest': longest_streak,
            'duration_trend': duration_trend,
            'intensity_trend': intensity_trend,
            'satisfaction_trend': satisfaction_trend
        }
    
    def get_exercise_recommendations_analysis(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze recommendation effectiveness
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with recommendation analysis
        """
        history = self._load_user_history(user_id)
        if not history:
            return {}
        
        recs = history.get('recommendation_history', [])
        user_feedback = history.get('user_feedback', {})
        
        if not recs:
            return {}
        
        total_recommendations = len(recs)
        
        # Unique exercises recommended
        unique_exercises = set(r.get('exercise_id') for r in recs)
        
        # Build satisfaction data - use user_feedback if available, else use simulated_satisfaction
        exercise_satisfactions = {}
        for rec in recs:
            ex_id = rec.get('exercise_id')
            if ex_id not in exercise_satisfactions:
                if ex_id in user_feedback:
                    exercise_satisfactions[ex_id] = user_feedback[ex_id]
                else:
                    # Use simulated satisfaction as fallback
                    exercise_satisfactions[ex_id] = rec.get('simulated_satisfaction', 0)
        
        total_completions = len(user_feedback) if user_feedback else len(exercise_satisfactions)
        acceptance_rate = (total_completions / total_recommendations * 100) if total_recommendations > 0 else 0
        
        # Top rated exercises
        top_rated = sorted(
            [[ex_id, round(score, 2)] for ex_id, score in exercise_satisfactions.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        satisfactions = list(exercise_satisfactions.values())
        avg_satisfaction = round(np.mean(satisfactions), 2) if satisfactions else 0
        
        return {
            'total_recommendations': total_recommendations,
            'total_completions': len(exercise_satisfactions),
            'unique_exercises': len(unique_exercises),
            'acceptance_rate': round(acceptance_rate, 1),
            'average_satisfaction': avg_satisfaction,
            'top_rated_exercises': top_rated,
            'exercise_satisfactions': exercise_satisfactions
        }
    
    def get_injury_impact_analysis(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze impact of injuries on exercise selection
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with injury impact analysis
        """
        if not self.system:
            return {}
        
        try:
            profile = self.system.user_manager.profiles.get(user_id)
            if not profile:
                return {}
            
            injuries = profile.injuries if hasattr(profile, 'injuries') else []
            
            history = self._load_user_history(user_id)
            if not history:
                return {'injuries': injuries, 'safe_exercise_count': 0}
            
            recs = history.get('recommendation_history', [])
            exercise_db = self.system.exercise_db
            
            safe_count = 0
            for rec in recs:
                ex_id = rec.get('exercise_id')
                try:
                    ex = exercise_db.get_exercise(ex_id)
                    if ex and ex.is_suitable_for(injuries):
                        safe_count += 1
                except:
                    pass
            
            return {
                'injuries': injuries,
                'safe_exercise_count': safe_count,
                'total_recommendations': len(recs)
            }
        except:
            return {}
    
    def get_time_analysis(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze when user exercises most (time of day patterns)
        
        Args:
            user_id: User ID
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with time analysis
        """
        history = self._load_user_history(user_id)
        if not history:
            return {}
        
        recs = history.get('recommendation_history', [])
        if not recs:
            return {}
        
        # Group by hour of day
        hourly_activity = defaultdict(int)
        daily_patterns = defaultdict(lambda: defaultdict(int))
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for rec in recs:
            ts = rec.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if start_date <= dt <= end_date:
                        hour = dt.hour
                        day_of_week = dt.strftime('%A')  # Monday, Tuesday, etc.
                        
                        hourly_activity[hour] += 1
                        daily_patterns[day_of_week][hour] += 1
                except:
                    pass
        
        if not hourly_activity:
            return {}
        
        # Find peak hours
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1])
        peak_hour_time = f"{peak_hour[0]:02d}:00"
        
        # Time of day distribution
        morning_hours = sum(hourly_activity.get(h, 0) for h in range(6, 12))  # 6AM-12PM
        afternoon_hours = sum(hourly_activity.get(h, 0) for h in range(12, 18))  # 12PM-6PM
        evening_hours = sum(hourly_activity.get(h, 0) for h in range(18, 24))  # 6PM-12AM
        night_hours = sum(hourly_activity.get(h, 0) for h in range(0, 6))  # 12AM-6AM
        
        total_sessions = sum(hourly_activity.values())
        
        # Weekly pattern
        weekly_data = {}
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            weekly_data[day] = dict(daily_patterns[day])
        
        return {
            'total_sessions_analyzed': total_sessions,
            'peak_hour': peak_hour_time,
            'peak_hour_sessions': peak_hour[1],
            'time_distribution': {
                'morning': morning_hours,
                'afternoon': afternoon_hours,
                'evening': evening_hours,
                'night': night_hours
            },
            'hourly_breakdown': dict(hourly_activity),
            'weekly_patterns': weekly_data,
            'most_active_day': max(daily_patterns.keys(), key=lambda d: sum(daily_patterns[d].values())) if daily_patterns else None
        }
    
    def get_comparison_metrics(self, user_ids: List[str], days_back: int = 7) -> Dict[str, Any]:
        """
        Compare metrics across multiple users
        
        Args:
            user_ids: List of user IDs to compare
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with comparison metrics
        """
        if not user_ids:
            return {}
        
        user_metrics = {}
        activity_rates = []
        exercise_counts = []
        durations = []
        
        for uid in user_ids:
            summary = self.get_weekly_summary(uid, days_back=days_back)
            if summary:
                user_metrics[uid] = {
                    'activity_rate': summary.get('activity_rate', 0),
                    'total_exercises': summary.get('total_exercises', 0),
                    'total_duration': summary.get('total_duration_minutes', 0),
                    'days_active': summary.get('days_active', 0)
                }
                activity_rates.append(summary.get('activity_rate', 0))
                exercise_counts.append(summary.get('total_exercises', 0))
                durations.append(summary.get('total_duration_minutes', 0))
        
        # Rankings
        rankings = {
            'most_active': sorted(user_metrics.items(), key=lambda x: x[1]['activity_rate'], reverse=True),
            'most_exercises': sorted(user_metrics.items(), key=lambda x: x[1]['total_exercises'], reverse=True),
            'longest_duration': sorted(user_metrics.items(), key=lambda x: x[1]['total_duration'], reverse=True)
        }
        
        return {
            'user_metrics': user_metrics,
            'rankings': {
                'most_active': [rankings['most_active'][0][0]] if rankings['most_active'] else [],
                'most_exercises': [rankings['most_exercises'][0][0]] if rankings['most_exercises'] else [],
                'longest_duration': [rankings['longest_duration'][0][0]] if rankings['longest_duration'] else []
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
            'total_sessions': 0,
            'total_duration_minutes': 0,
            'total_calories_burned': 0,
            'average_intensity': 0,
            'average_satisfaction': 0,
            'sessions': [],
            'exercises': [],
            'muscles_worked': {},
            'time_distribution': {
                'morning': 0,
                'afternoon': 0,
                'evening': 0,
                'night': 0
            },
            'status': 'no_activity'
        }
    
    def _empty_weekly_summary(self, days_back: int) -> Dict:
        """Return empty weekly summary structure"""
        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()
        
        return {
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'days_active': 0,
            'activity_rate': 0,
            'total_exercises': 0,
            'total_duration_minutes': 0,
            'total_calories_burned': 0,
            'average_duration_per_session': 0,
            'most_frequent_exercises': [],
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
    
    def _calculate_streak(self, dates: List[datetime], current: bool = True) -> int:
        """
        Calculate activity streak
        
        Args:
            dates: List of active dates
            current: If True, calculate current streak; if False, longest streak
            
        Returns:
            Number of consecutive active days
        """
        if not dates:
            return 0
        
        dates = sorted(dates)
        
        if current:
            # Calculate current streak from today backwards
            today = datetime.now().date()
            streak = 0
            for i in range(365):
                check_date = today - timedelta(days=i)
                if any(d.date() == check_date for d in dates):
                    streak += 1
                else:
                    break
            return streak
        else:
            # Calculate longest streak
            max_streak = 1
            current_streak = 1
            
            for i in range(1, len(dates)):
                if (dates[i] - dates[i-1]).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            
            return max_streak
