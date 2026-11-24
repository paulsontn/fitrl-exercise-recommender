"""
Training Module for RL Agent
"""

import numpy as np
from typing import Tuple, List
from exercise_env import ExerciseRecommendationEnv
from rl_agent import DQNAgent, PolicyGradientAgent
from user_profile import UserProfile


class ExerciseRecommendationTrainer:
    """Trainer for exercise recommendation RL agent"""
    
    def __init__(self, agent: DQNAgent, env: ExerciseRecommendationEnv):
        """
        Initialize trainer
        
        Args:
            agent: RL agent to train
            env: Gym environment
        """
        self.agent = agent
        self.env = env
        self.episode_rewards = []
        self.episode_lengths = []
    
    def train(self, num_episodes: int, update_frequency: int = 4) -> Tuple[List, List]:
        """
        Train the agent
        
        Args:
            num_episodes: Number of episodes to train
            update_frequency: Frequency of target network updates
            
        Returns:
            List of episode rewards and lengths
        """
        for episode in range(num_episodes):
            state, _ = self.env.reset()
            episode_reward = 0
            episode_length = 0
            
            done = False
            while not done:
                # Select and perform action
                action = self.agent.act(state)
                next_state, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated
                
                # Store experience
                self.agent.remember(state, action, reward, next_state, done)
                
                # Train on batch
                self.agent.replay(self.agent.batch_size)
                
                episode_reward += reward
                episode_length += 1
                state = next_state
            
            # Update target network
            if (episode + 1) % update_frequency == 0:
                self.agent.update_target_network()
            
            # Store metrics
            self.episode_rewards.append(episode_reward)
            self.episode_lengths.append(episode_length)
            
            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(self.episode_rewards[-10:])
                print(f"Episode {episode + 1}/{num_episodes} - Avg Reward: {avg_reward:.2f}")
        
        return self.episode_rewards, self.episode_lengths


class PolicyGradientTrainer:
    """Trainer for Policy Gradient Agent"""
    
    def __init__(self, agent: PolicyGradientAgent, env: ExerciseRecommendationEnv):
        """
        Initialize trainer
        
        Args:
            agent: Policy gradient agent to train
            env: Gym environment
        """
        self.agent = agent
        self.env = env
        self.episode_rewards = []
    
    def train(self, num_episodes: int) -> List[float]:
        """
        Train the agent using REINFORCE
        
        Args:
            num_episodes: Number of episodes to train
            
        Returns:
            List of episode rewards
        """
        for episode in range(num_episodes):
            state, _ = self.env.reset()
            done = False
            
            while not done:
                # Select action
                action, log_prob = self.agent.act(state)
                
                # Perform action
                next_state, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated
                
                # Remember experience
                self.agent.remember(log_prob, reward)
                
                state = next_state
            
            # Update policy at end of episode
            self.agent.update()
            
            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(self.agent.training_rewards[-10:])
                print(f"Episode {episode + 1}/{num_episodes} - Avg Reward: {avg_reward:.2f}")
        
        return self.agent.training_rewards
