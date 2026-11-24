"""
User Profile Module
Defines different user types and their characteristics
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List
import numpy as np


class FitnessLevel(Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3


class UserGoal(Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    FLEXIBILITY = "flexibility"
    GENERAL_FITNESS = "general_fitness"


@dataclass
class UserProfile:
    """Represents a user's fitness profile"""
    user_id: str
    age: int
    fitness_level: FitnessLevel
    goals: List[UserGoal]
    available_time: float  # minutes per session
    injuries: List[str]  # list of injuries/constraints
    equipment_access: List[str]  # available equipment
    preferred_exercises: List[str]  # user's favorite exercises
    # Daily condition metrics (optional, used by environment reward logic)
    fatigue: float = 0.0          # 0 (rested) - 10 (exhausted)
    soreness: float = 0.0         # 0 (no soreness) - 10 (very sore)
    sleep_hours: float = 8.0      # hours slept last night
    resting_heart_rate: int = 60  # bpm
    
    def __post_init__(self):
        """Validate profile"""
        if self.age < 13 or self.age > 120:
            raise ValueError("Invalid age")
        if self.available_time < 5:
            raise ValueError("Available time must be at least 5 minutes")

    def to_dict(self) -> Dict:
        """Convert profile to dictionary"""
        return {
            'user_id': self.user_id,
            'age': self.age,
            'fitness_level': self.fitness_level.value,
            'goals': [goal.value for goal in self.goals],
            'available_time': self.available_time,
            'injuries': self.injuries,
            'equipment_access': self.equipment_access,
            'preferred_exercises': self.preferred_exercises
        }


class UserProfileManager:
    """Manages user profiles"""
    
    def __init__(self):
        self.profiles: Dict[str, UserProfile] = {}
    
    def create_profile(self, user_profile: UserProfile) -> UserProfile:
        """Create or update a user profile"""
        self.profiles[user_profile.user_id] = user_profile
        return user_profile
    
    def get_profile(self, user_id: str) -> UserProfile:
        """Retrieve a user profile"""
        if user_id not in self.profiles:
            raise ValueError(f"User {user_id} not found")
        return self.profiles[user_id]
    
    def update_fitness_level(self, user_id: str, new_level: FitnessLevel):
        """Update user's fitness level"""
        profile = self.get_profile(user_id)
        profile.fitness_level = new_level
    
    def add_goal(self, user_id: str, goal: UserGoal):
        """Add a fitness goal"""
        profile = self.get_profile(user_id)
        if goal not in profile.goals:
            profile.goals.append(goal)
    
    def add_injury(self, user_id: str, injury: str):
        """Add an injury/constraint"""
        profile = self.get_profile(user_id)
        if injury not in profile.injuries:
            profile.injuries.append(injury)
    
    def remove_injury(self, user_id: str, injury: str):
        """Remove an injury/constraint"""
        profile = self.get_profile(user_id)
        if injury in profile.injuries:
            profile.injuries.remove(injury)
