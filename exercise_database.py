"""
Exercise Database Module
Defines exercises and their properties
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum


class MuscleGroup(Enum):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    FOREARMS = "forearms"
    ABS = "abs"
    QUADRICEPS = "quadriceps"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    CALVES = "calves"
    CARDIO = "cardio"


class ExerciseDifficulty(Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3


@dataclass
class Exercise:
    """Represents an exercise"""
    exercise_id: str
    name: str
    description: str
    primary_muscles: Set[MuscleGroup]
    secondary_muscles: Set[MuscleGroup]
    difficulty: ExerciseDifficulty
    duration_minutes: float  # typical duration
    equipment_required: List[str]
    intensity_level: int  # 1-10
    calories_burned: float  # approximate per minute
    contraindications: List[str]  # injuries/conditions to avoid
    sets: int = 3  # default sets
    reps: int = 12  # default reps (for strength) or duration for cardio
    variations: List[str] = field(default_factory=list)
    
    def is_suitable_for(self, injuries: List[str]) -> bool:
        """Check if exercise is suitable given injuries"""
        return not any(injury in self.contraindications for injury in injuries)
    
    def requires_equipment(self, available_equipment: List[str]) -> bool:
        """Check if user has required equipment"""
        return all(eq in available_equipment for eq in self.equipment_required)


class ExerciseDatabase:
    """Database of exercises"""
    
    def __init__(self):
        self.exercises: Dict[str, Exercise] = {}
        self._load_default_exercises()
    
    def _load_default_exercises(self):
        """Load a default set of exercises"""
        default_exercises = [
            # Beginner cardio
            Exercise(
                exercise_id="walking",
                name="Walking",
                description="Brisk walking at moderate pace",
                primary_muscles={MuscleGroup.CARDIO, MuscleGroup.GLUTES},
                secondary_muscles={MuscleGroup.QUADRICEPS, MuscleGroup.HAMSTRINGS},
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=30,
                equipment_required=[],
                intensity_level=3,
                calories_burned=4,
                contraindications=[],
                sets=1,
                reps=30  # minutes
            ),
            
            Exercise(
                exercise_id="jogging",
                name="Jogging",
                description="Light to moderate jogging",
                primary_muscles={MuscleGroup.CARDIO, MuscleGroup.GLUTES},
                secondary_muscles={MuscleGroup.QUADRICEPS, MuscleGroup.HAMSTRINGS},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=30,
                equipment_required=[],
                intensity_level=6,
                calories_burned=8,
                contraindications=["knee_pain", "ankle_pain"],
                sets=1,
                reps=30  # minutes
            ),
            
            # Strength - Upper body
            Exercise(
                exercise_id="pushups",
                name="Push-ups",
                description="Standard push-ups for chest and triceps",
                primary_muscles={MuscleGroup.CHEST, MuscleGroup.TRICEPS},
                secondary_muscles={MuscleGroup.SHOULDERS, MuscleGroup.ABS},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=15,
                equipment_required=[],
                intensity_level=6,
                calories_burned=7,
                contraindications=["shoulder_pain", "wrist_pain"],
                sets=3,
                reps=12
            ),
            
            Exercise(
                exercise_id="bench_press",
                name="Bench Press",
                description="Barbell or dumbbell bench press",
                primary_muscles={MuscleGroup.CHEST},
                secondary_muscles={MuscleGroup.TRICEPS, MuscleGroup.SHOULDERS},
                difficulty=ExerciseDifficulty.ADVANCED,
                duration_minutes=20,
                equipment_required=["dumbbells", "barbell", "bench"],
                intensity_level=8,
                calories_burned=8,
                contraindications=["shoulder_pain", "chest_pain"],
                sets=4,
                reps=8
            ),
            
            Exercise(
                exercise_id="dumbbell_rows",
                name="Dumbbell Rows",
                description="Single or double arm dumbbell rows",
                primary_muscles={MuscleGroup.BACK},
                secondary_muscles={MuscleGroup.BICEPS},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=15,
                equipment_required=["dumbbells"],
                intensity_level=6,
                calories_burned=6,
                contraindications=["back_pain", "lower_back_pain"],
                sets=3,
                reps=10
            ),
            
            Exercise(
                exercise_id="pull_ups",
                name="Pull-ups",
                description="Standard pull-ups for back and biceps",
                primary_muscles={MuscleGroup.BACK, MuscleGroup.BICEPS},
                secondary_muscles={MuscleGroup.SHOULDERS},
                difficulty=ExerciseDifficulty.ADVANCED,
                duration_minutes=15,
                equipment_required=["pull_up_bar"],
                intensity_level=8,
                calories_burned=9,
                contraindications=["shoulder_pain", "wrist_pain"],
                sets=3,
                reps=8
            ),
            
            Exercise(
                exercise_id="bicep_curls",
                name="Bicep Curls",
                description="Dumbbell bicep curls",
                primary_muscles={MuscleGroup.BICEPS},
                secondary_muscles={MuscleGroup.FOREARMS},
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=12,
                equipment_required=["dumbbells"],
                intensity_level=5,
                calories_burned=4,
                contraindications=["elbow_pain"],
                sets=3,
                reps=12
            ),
            
            Exercise(
                exercise_id="tricep_dips",
                name="Tricep Dips",
                description="Bodyweight tricep dips",
                primary_muscles={MuscleGroup.TRICEPS},
                secondary_muscles={MuscleGroup.CHEST, MuscleGroup.SHOULDERS},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=12,
                equipment_required=["bench", "dip_bars"],
                intensity_level=6,
                calories_burned=6,
                contraindications=["shoulder_pain", "elbow_pain"],
                sets=3,
                reps=10
            ),
            
            # Lower body
            Exercise(
                exercise_id="squats",
                name="Squats",
                description="Bodyweight or weighted squats",
                primary_muscles={MuscleGroup.QUADRICEPS, MuscleGroup.GLUTES},
                secondary_muscles={MuscleGroup.HAMSTRINGS},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=15,
                equipment_required=[],
                intensity_level=7,
                calories_burned=8,
                contraindications=["knee_pain"],
                sets=4,
                reps=12
            ),
            
            Exercise(
                exercise_id="lunges",
                name="Lunges",
                description="Forward or reverse lunges",
                primary_muscles={MuscleGroup.QUADRICEPS, MuscleGroup.GLUTES},
                secondary_muscles={MuscleGroup.HAMSTRINGS},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=15,
                equipment_required=[],
                intensity_level=6,
                calories_burned=7,
                contraindications=["knee_pain", "ankle_pain"],
                sets=3,
                reps=10
            ),
            
            Exercise(
                exercise_id="deadlifts",
                name="Deadlifts",
                description="Barbell deadlifts",
                primary_muscles={MuscleGroup.GLUTES, MuscleGroup.HAMSTRINGS},
                secondary_muscles={MuscleGroup.BACK},
                difficulty=ExerciseDifficulty.ADVANCED,
                duration_minutes=20,
                equipment_required=["barbell"],
                intensity_level=9,
                calories_burned=9,
                contraindications=["lower_back_pain", "back_pain"],
                sets=4,
                reps=6
            ),
            
            Exercise(
                exercise_id="leg_press",
                name="Leg Press",
                description="Machine leg press",
                primary_muscles={MuscleGroup.QUADRICEPS, MuscleGroup.GLUTES},
                secondary_muscles={MuscleGroup.HAMSTRINGS},
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=15,
                equipment_required=["leg_press_machine"],
                intensity_level=6,
                calories_burned=7,
                contraindications=["knee_pain"],
                sets=3,
                reps=12
            ),
            
            # Flexibility
            Exercise(
                exercise_id="yoga",
                name="Yoga",
                description="General yoga session",
                primary_muscles={MuscleGroup.CARDIO},
                secondary_muscles=set(MuscleGroup),
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=45,
                equipment_required=[],
                intensity_level=3,
                calories_burned=3,
                contraindications=[],
                sets=1,
                reps=45  # minutes
            ),
            
            Exercise(
                exercise_id="stretching",
                name="Stretching",
                description="Full body stretching routine",
                primary_muscles=set(),
                secondary_muscles=set(MuscleGroup),
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=20,
                equipment_required=[],
                intensity_level=2,
                calories_burned=1,
                contraindications=[],
                sets=1,
                reps=20  # minutes
            ),
            
            # Core
            Exercise(
                exercise_id="planks",
                name="Planks",
                description="Front planks and variations",
                primary_muscles={MuscleGroup.ABS},
                secondary_muscles={MuscleGroup.CHEST, MuscleGroup.SHOULDERS},
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=12,
                equipment_required=[],
                intensity_level=5,
                calories_burned=5,
                contraindications=["shoulder_pain"],
                sets=3,
                reps=60  # seconds
            ),
            
            Exercise(
                exercise_id="crunches",
                name="Crunches",
                description="Standard abdominal crunches",
                primary_muscles={MuscleGroup.ABS},
                secondary_muscles=set(),
                difficulty=ExerciseDifficulty.BEGINNER,
                duration_minutes=10,
                equipment_required=[],
                intensity_level=4,
                calories_burned=3,
                contraindications=["neck_pain"],
                sets=3,
                reps=15
            ),
            
            # Cardio - Cycling
            Exercise(
                exercise_id="cycling",
                name="Cycling",
                description="Stationary or outdoor cycling at moderate pace",
                primary_muscles={MuscleGroup.CARDIO, MuscleGroup.QUADRICEPS},
                secondary_muscles={MuscleGroup.GLUTES, MuscleGroup.HAMSTRINGS, MuscleGroup.CALVES},
                difficulty=ExerciseDifficulty.INTERMEDIATE,
                duration_minutes=30,
                equipment_required=["bicycle"],
                intensity_level=6,
                calories_burned=7,
                contraindications=["knee_pain"],
                sets=1,
                reps=30  # minutes
            ),
            
            # Cardio - Running Intervals
            Exercise(
                exercise_id="run_intervals",
                name="Running Intervals",
                description="High-intensity interval training with running",
                primary_muscles={MuscleGroup.CARDIO, MuscleGroup.GLUTES},
                secondary_muscles={MuscleGroup.QUADRICEPS, MuscleGroup.HAMSTRINGS, MuscleGroup.CALVES},
                difficulty=ExerciseDifficulty.ADVANCED,
                duration_minutes=20,
                equipment_required=[],
                intensity_level=9,
                calories_burned=12,
                contraindications=["knee_pain", "ankle_pain", "lower_back_pain"],
                sets=1,
                reps=20  # minutes
            ),
        ]
        
        for exercise in default_exercises:
            self.add_exercise(exercise)
    
    def add_exercise(self, exercise: Exercise):
        """Add an exercise to the database"""
        self.exercises[exercise.exercise_id] = exercise
    
    def get_exercise(self, exercise_id: str) -> Exercise:
        """Get an exercise by ID"""
        if exercise_id not in self.exercises:
            raise ValueError(f"Exercise {exercise_id} not found")
        return self.exercises[exercise_id]
    
    def get_all_exercises(self) -> List[Exercise]:
        """Get all exercises"""
        return list(self.exercises.values())
    
    def filter_by_difficulty(self, difficulty: ExerciseDifficulty) -> List[Exercise]:
        """Filter exercises by difficulty level"""
        return [ex for ex in self.exercises.values() if ex.difficulty == difficulty]
    
    def filter_by_muscle_group(self, muscle: MuscleGroup) -> List[Exercise]:
        """Filter exercises by primary muscle group"""
        return [ex for ex in self.exercises.values() if muscle in ex.primary_muscles]
    
    def get_suitable_exercises(self, injuries: List[str], 
                              available_equipment: List[str],
                              difficulty: ExerciseDifficulty) -> List[Exercise]:
        """Get exercises suitable for a user"""
        suitable = []
        for exercise in self.exercises.values():
            # Allow exercises at or below user's difficulty level
            difficulty_ok = exercise.difficulty.value <= difficulty.value
            if (difficulty_ok and
                exercise.is_suitable_for(injuries) and
                exercise.requires_equipment(available_equipment)):
                suitable.append(exercise)
        return suitable
