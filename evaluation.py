"""
Evaluation and Testing Module
Comprehensive evaluation of the recommendation system
"""

import numpy as np
from typing import List, Dict
import matplotlib.pyplot as plt
from user_profile import UserProfile, FitnessLevel, UserGoal
from exercise_database import ExerciseDatabase
from recommendation_system import RecommendationSystem


class SystemEvaluator:
    """Evaluates the recommendation system performance"""
    
    def __init__(self):
        self.system = RecommendationSystem(agent_path="trained_agent.pt")
        self.exercise_db = ExerciseDatabase()
        self.evaluation_metrics = {}
    
    def evaluate_goal_alignment(self, num_users: int = 10) -> Dict[str, float]:
        """
        Evaluate how well recommendations align with user goals
        
        Args:
            num_users: Number of test users
            
        Returns:
            Alignment metrics
        """
        print("\n" + "="*60)
        print("EVALUATING GOAL ALIGNMENT")
        print("="*60)
        
        alignment_scores = []
        goal_matches = {goal.value: [] for goal in UserGoal}
        
        # Create diverse test users
        test_users = self._create_test_users(num_users)
        
        for user_profile in test_users:
            recommender = self.system.register_user(user_profile)
            recommendations = recommender.get_recommendations(num_recommendations=5)
            
            # Check goal alignment for each recommendation
            for rec in recommendations:
                exercise = self.exercise_db.get_exercise(rec['exercise_id'])
                
                # Score alignment with goals
                goal_score = 0
                for goal in user_profile.goals:
                    if self._is_aligned_with_goal(exercise, goal):
                        goal_score += 1
                    goal_matches[goal.value].append(goal_score > 0)
                
                alignment_scores.append(goal_score / max(len(user_profile.goals), 1))
        
        # Calculate metrics
        metrics = {
            'mean_alignment': np.mean(alignment_scores),
            'alignment_std': np.std(alignment_scores),
            'min_alignment': np.min(alignment_scores),
            'max_alignment': np.max(alignment_scores)
        }
        
        # Per-goal metrics
        for goal, scores in goal_matches.items():
            if scores:
                metrics[f'{goal}_alignment_rate'] = np.mean(scores)
        
        print(f"Mean Goal Alignment: {metrics['mean_alignment']:.2%}")
        for goal, rate in metrics.items():
            if 'alignment_rate' in goal:
                print(f"  {goal}: {rate:.2%}")
        
        return metrics
    
    def evaluate_safety(self, num_users: int = 10) -> Dict[str, float]:
        """
        Evaluate safety of recommendations (injury contraindications)
        
        Args:
            num_users: Number of test users
            
        Returns:
            Safety metrics
        """
        print("\n" + "="*60)
        print("EVALUATING SAFETY")
        print("="*60)
        
        unsafe_recommendations = 0
        total_recommendations = 0
        
        test_users = self._create_test_users(num_users)
        
        for user_profile in test_users:
            recommender = self.system.register_user(user_profile)
            recommendations = recommender.get_recommendations(num_recommendations=5)
            
            for rec in recommendations:
                exercise = self.exercise_db.get_exercise(rec['exercise_id'])
                total_recommendations += 1
                
                # Check contraindications
                if not exercise.is_suitable_for(user_profile.injuries):
                    unsafe_recommendations += 1
        
        safety_rate = (total_recommendations - unsafe_recommendations) / total_recommendations
        
        metrics = {
            'safety_rate': safety_rate,
            'unsafe_recommendations': unsafe_recommendations,
            'total_recommendations': total_recommendations
        }
        
        print(f"Safety Rate: {safety_rate:.2%}")
        print(f"Unsafe Recommendations: {unsafe_recommendations}/{total_recommendations}")
        
        return metrics
    
    def evaluate_diversity(self, num_users: int = 10) -> Dict[str, float]:
        """
        Evaluate diversity of recommendations (exercises don't repeat much)
        
        Args:
            num_users: Number of test users
            
        Returns:
            Diversity metrics
        """
        print("\n" + "="*60)
        print("EVALUATING DIVERSITY")
        print("="*60)
        
        diversity_scores = []
        
        test_users = self._create_test_users(num_users)
        
        for user_profile in test_users:
            recommender = self.system.register_user(user_profile)
            
            # Get multiple recommendations in sequence
            all_recommendations = []
            for _ in range(5):  # Get 5 sets of recommendations
                recs = recommender.get_recommendations(num_recommendations=5)
                all_recommendations.extend([r['exercise_id'] for r in recs])
            
            # Calculate diversity (unique exercises / total recommendations)
            unique_count = len(set(all_recommendations))
            total_count = len(all_recommendations)
            diversity = unique_count / total_count
            diversity_scores.append(diversity)
        
        metrics = {
            'mean_diversity': np.mean(diversity_scores),
            'diversity_std': np.std(diversity_scores),
            'min_diversity': np.min(diversity_scores),
            'max_diversity': np.max(diversity_scores)
        }
        
        print(f"Mean Diversity Score: {metrics['mean_diversity']:.2%}")
        print(f"  (Higher is better - more exercise variety)")
        
        return metrics
    
    def evaluate_time_fit(self, num_users: int = 10) -> Dict[str, float]:
        """
        Evaluate how well recommendations fit user's available time
        
        Args:
            num_users: Number of test users
            
        Returns:
            Time fit metrics
        """
        print("\n" + "="*60)
        print("EVALUATING TIME FIT")
        print("="*60)
        
        time_fits = []
        
        test_users = self._create_test_users(num_users)
        
        for user_profile in test_users:
            recommender = self.system.register_user(user_profile)
            recommendations = recommender.get_recommendations(num_recommendations=5)
            
            for rec in recommendations:
                exercise = self.exercise_db.get_exercise(rec['exercise_id'])
                
                # Calculate time fit (how close to available time)
                time_diff = abs(exercise.duration_minutes - user_profile.available_time)
                fit_score = max(0, 1 - (time_diff / user_profile.available_time))
                time_fits.append(fit_score)
        
        metrics = {
            'mean_time_fit': np.mean(time_fits),
            'time_fit_std': np.std(time_fits),
            'acceptable_time_fit_rate': np.mean([f >= 0.7 for f in time_fits])
        }
        
        print(f"Mean Time Fit Score: {metrics['mean_time_fit']:.2%}")
        print(f"Exercises with acceptable time fit (≥70%): {metrics['acceptable_time_fit_rate']:.2%}")
        
        return metrics
    
    def evaluate_difficulty_match(self, num_users: int = 10) -> Dict[str, float]:
        """
        Evaluate if recommendations match user's fitness level
        
        Args:
            num_users: Number of test users
            
        Returns:
            Difficulty matching metrics
        """
        print("\n" + "="*60)
        print("EVALUATING DIFFICULTY MATCH")
        print("="*60)
        
        matched = 0
        total = 0
        
        test_users = self._create_test_users(num_users)
        
        for user_profile in test_users:
            recommender = self.system.register_user(user_profile)
            recommendations = recommender.get_recommendations(num_recommendations=5)
            
            for rec in recommendations:
                exercise = self.exercise_db.get_exercise(rec['exercise_id'])
                total += 1
                
                # Check if difficulty matches
                if exercise.difficulty == user_profile.fitness_level:
                    matched += 1
        
        match_rate = matched / total if total > 0 else 0
        
        metrics = {
            'difficulty_match_rate': match_rate,
            'matched_exercises': matched,
            'total_exercises': total
        }
        
        print(f"Difficulty Match Rate: {match_rate:.2%}")
        print(f"Matched: {matched}/{total}")
        
        return metrics
    
    def run_full_evaluation(self, num_users: int = 10) -> Dict[str, Dict]:
        """
        Run complete evaluation suite
        
        Args:
            num_users: Number of test users
            
        Returns:
            Dictionary of all evaluation metrics
        """
        print("\n" + "="*80)
        print("COMPREHENSIVE SYSTEM EVALUATION")
        print("="*80)
        
        all_metrics = {}
        
        # Run evaluations
        all_metrics['goal_alignment'] = self.evaluate_goal_alignment(num_users)
        all_metrics['safety'] = self.evaluate_safety(num_users)
        all_metrics['diversity'] = self.evaluate_diversity(num_users)
        all_metrics['time_fit'] = self.evaluate_time_fit(num_users)
        all_metrics['difficulty'] = self.evaluate_difficulty_match(num_users)
        
        # Print summary
        self._print_summary(all_metrics)
        
        return all_metrics
    
    def _create_test_users(self, num_users: int) -> List[UserProfile]:
        """Create diverse test users"""
        users = []
        
        # Beginner
        users.append(UserProfile(
            user_id=f"test_beginner_001",
            age=25,
            fitness_level=FitnessLevel.BEGINNER,
            goals=[UserGoal.GENERAL_FITNESS],
            available_time=30,
            injuries=[],
            equipment_access=[],
            preferred_exercises=["walking", "stretching"]
        ))
        
        # Intermediate with injuries
        users.append(UserProfile(
            user_id=f"test_intermediate_001",
            age=35,
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=[UserGoal.MUSCLE_GAIN, UserGoal.WEIGHT_LOSS],
            available_time=45,
            injuries=["lower_back_pain"],
            equipment_access=["dumbbells", "barbell"],
            preferred_exercises=["bench_press"]
        ))
        
        # Advanced with limited equipment
        users.append(UserProfile(
            user_id=f"test_advanced_001",
            age=28,
            fitness_level=FitnessLevel.ADVANCED,
            goals=[UserGoal.MUSCLE_GAIN],
            available_time=60,
            injuries=[],
            equipment_access=[],
            preferred_exercises=["pull_ups", "push_ups"]
        ))
        
        # Flexibility focused
        users.append(UserProfile(
            user_id=f"test_flexibility_001",
            age=45,
            fitness_level=FitnessLevel.BEGINNER,
            goals=[UserGoal.FLEXIBILITY],
            available_time=45,
            injuries=["knee_pain"],
            equipment_access=[],
            preferred_exercises=["yoga", "stretching"]
        ))
        
        # Cardio focused
        users.append(UserProfile(
            user_id=f"test_cardio_001",
            age=30,
            fitness_level=FitnessLevel.INTERMEDIATE,
            goals=[UserGoal.WEIGHT_LOSS, UserGoal.ENDURANCE],
            available_time=30,
            injuries=[],
            equipment_access=[],
            preferred_exercises=["jogging", "walking"]
        ))
        
        # Generate additional random users
        while len(users) < num_users:
            equipment_options = [
                [],
                ["dumbbells"],
                ["dumbbells", "barbell"],
                ["dumbbells", "barbell", "bench"]
            ]
            users.append(UserProfile(
                user_id=f"test_random_{len(users):03d}",
                age=np.random.randint(18, 65),
                fitness_level=np.random.choice(list(FitnessLevel)),
                goals=[np.random.choice(list(UserGoal))],
                available_time=np.random.choice([20, 30, 45, 60]),
                injuries=[],
                equipment_access=equipment_options[np.random.randint(0, len(equipment_options))],
                preferred_exercises=[]
            ))
        
        return users[:num_users]
    
    def _is_aligned_with_goal(self, exercise, goal: UserGoal) -> bool:
        """Check if exercise aligns with goal"""
        if goal == UserGoal.MUSCLE_GAIN:
            return exercise.intensity_level >= 5
        elif goal == UserGoal.WEIGHT_LOSS:
            return exercise.intensity_level >= 6 and exercise.calories_burned >= 5
        elif goal == UserGoal.ENDURANCE:
            return exercise.exercise_id in ["walking", "jogging", "yoga"]
        elif goal == UserGoal.FLEXIBILITY:
            return exercise.exercise_id in ["yoga", "stretching"]
        else:
            return True
    
    def _print_summary(self, all_metrics: Dict[str, Dict]):
        """Print evaluation summary"""
        print("\n" + "="*80)
        print("EVALUATION SUMMARY")
        print("="*80)
        
        print("\n📊 KEY METRICS:")
        
        print(f"  ✓ Safety: {all_metrics['safety']['safety_rate']:.2%}")
        print(f"  ✓ Goal Alignment: {all_metrics['goal_alignment']['mean_alignment']:.2%}")
        print(f"  ✓ Diversity: {all_metrics['diversity']['mean_diversity']:.2%}")
        print(f"  ✓ Time Fit: {all_metrics['time_fit']['mean_time_fit']:.2%}")
        print(f"  ✓ Difficulty Match: {all_metrics['difficulty']['difficulty_match_rate']:.2%}")
        
        # Calculate overall score
        overall_score = (
            all_metrics['safety']['safety_rate'] * 0.3 +
            all_metrics['goal_alignment']['mean_alignment'] * 0.25 +
            all_metrics['diversity']['mean_diversity'] * 0.15 +
            all_metrics['time_fit']['mean_time_fit'] * 0.15 +
            all_metrics['difficulty']['difficulty_match_rate'] * 0.15
        )
        
        print(f"\n🎯 OVERALL SCORE: {overall_score:.2%}")
        
        if overall_score >= 0.85:
            print("   Status: ✅ EXCELLENT")
        elif overall_score >= 0.75:
            print("   Status: ✅ GOOD")
        elif overall_score >= 0.60:
            print("   Status: ⚠️  FAIR")
        else:
            print("   Status: ❌ NEEDS IMPROVEMENT")


if __name__ == "__main__":
    evaluator = SystemEvaluator()
    metrics = evaluator.run_full_evaluation(num_users=10)
    
    print("\n" + "="*80)
    print("Evaluation complete!")
    print("="*80)
