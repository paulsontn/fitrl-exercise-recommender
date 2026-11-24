"""
Configuration file for the Exercise Recommendation System
"""

# RL Agent Configuration
RL_CONFIG = {
    'learning_rate': 0.001,
    'gamma': 0.99,
    'epsilon': 1.0,
    'epsilon_decay': 0.995,
    'epsilon_min': 0.01,
    'hidden_size': 128,
    'batch_size': 32,
    'memory_size': 10000,
    'update_frequency': 4
}

# Training Configuration
TRAINING_CONFIG = {
    'num_episodes': 100,
    'state_size': 15,
    'max_steps_per_episode': 30,
    'save_every_n_episodes': 50
}

# Environment Configuration
ENV_CONFIG = {
    'state_size': 15,
    'max_steps': 30,
    'reward_weights': {
        'user_satisfaction': 1.0,
        'goal_alignment': 1.0,
        'variety_bonus': 0.1,
        'repetition_penalty': -0.5
    }
}

# API Configuration
API_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,
    'json_sort_keys': False
}

# Default User Configuration
DEFAULT_USER_CONFIG = {
    'available_time': 30,
    'injuries': [],
    'equipment_access': [],
    'preferred_exercises': []
}

# Exercise Recommendation Configuration
RECOMMENDATION_CONFIG = {
    'default_num_recommendations': 5,
    'min_recommendations': 1,
    'max_recommendations': 10,
    'default_workout_duration': 45,
    'min_workout_duration': 15,
    'max_workout_duration': 120
}

# File Paths
FILE_PATHS = {
    'trained_agent': 'trained_agent.pt',
    'training_history': 'training_history.json',
    'user_data': 'user_data.json',
    'recommendations_log': 'recommendations.log'
}
