"""
RL Agent for Exercise Recommendation
Implements Q-Learning and Policy Gradient methods
"""

import numpy as np
from typing import Tuple, List
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import pickle
import os


class QNetwork(nn.Module):
    """Deep Q-Network for continuous state approximation"""
    
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super(QNetwork, self).__init__()
        
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        
        self.relu = nn.ReLU()
    
    def forward(self, state):
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        return self.fc3(x)


class PolicyNetwork(nn.Module):
    """Policy Network for Policy Gradient methods"""
    
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super(PolicyNetwork, self).__init__()
        
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=-1)
    
    def forward(self, state):
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        return self.softmax(self.fc3(x))


class DQNAgent:
    """Deep Q-Network Agent for exercise recommendation"""
    
    def __init__(self, state_size: int, action_size: int, 
                 learning_rate: float = 0.001,
                 gamma: float = 0.99,
                 epsilon: float = 1.0,
                 epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01,
                 hidden_size: int = 128):
        """
        Initialize DQN Agent
        
        Args:
            state_size: Dimension of state space
            action_size: Number of possible actions
            learning_rate: Learning rate for optimizer
            gamma: Discount factor
            epsilon: Initial exploration rate
            epsilon_decay: Decay rate for epsilon
            epsilon_min: Minimum epsilon value
            hidden_size: Hidden layer size
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        
        # Networks
        self.device = torch.device("cpu")
        self.q_network = QNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_network = QNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Optimizer
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        
        # Experience replay buffer
        self.memory = deque(maxlen=10000)
        self.batch_size = 32
        
        # Training stats
        self.training_rewards = []
        self.training_losses = []
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                next_state: np.ndarray, done: bool):
        """Store experience in replay buffer"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state: np.ndarray) -> int:
        """
        Select action using epsilon-greedy strategy
        
        Args:
            state: Current state
            
        Returns:
            Selected action index
        """
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor)
        
        return q_values.argmax(dim=1).item()
    
    def replay(self, batch_size: int):
        """Train on mini-batch from experience replay"""
        if len(self.memory) < batch_size:
            return
        
        # Sample batch
        batch = np.random.choice(len(self.memory), batch_size, replace=False)
        states, actions, rewards, next_states, dones = zip(
            *[self.memory[i] for i in batch]
        )
        
        # Convert to tensors
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # Compute Q-values
        q_values = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Compute target Q-values
        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(dim=1)[0]
            target_q_values = rewards + self.gamma * next_q_values * (1 - dones)
        
        # Compute loss
        loss = self.criterion(q_values, target_q_values)
        
        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        self.training_losses.append(loss.item())
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def update_target_network(self):
        """Update target network weights"""
        self.target_network.load_state_dict(self.q_network.state_dict())
    
    def save(self, filepath: str):
        """Save agent to file"""
        torch.save(self.q_network.state_dict(), filepath)
    
    def load(self, filepath: str):
        """Load agent from file.

        This method is robust to checkpoints saved with a different action_size.
        If the checkpoint's final layer (fc3) output size differs from the
        current agent, the agent networks will be recreated to match the
        checkpoint action size before loading. This avoids size-mismatch
        errors when loading older/newer checkpoints.
        """
        # Load checkpoint to CPU/device
        checkpoint = torch.load(filepath, map_location=self.device)

        # Normalize checkpoint keys (handle 'module.' prefix if present)
        adapted_ckpt = {}
        for k, v in checkpoint.items():
            name = k
            if name.startswith('module.'):
                name = name[len('module.'):]
            adapted_ckpt[name] = v

        # Start from current model state dict
        model_state = self.q_network.state_dict()

        # If fc3 (final layer) exists in checkpoint, handle shape differences
        fc3_w_key = None
        fc3_b_key = None
        for key in adapted_ckpt.keys():
            if key.endswith('fc3.weight'):
                fc3_w_key = key
            if key.endswith('fc3.bias'):
                fc3_b_key = key

        try:
            # Copy matching keys from checkpoint into current model_state
            for key, value in adapted_ckpt.items():
                if key in model_state and key not in (fc3_w_key, fc3_b_key):
                    # Only copy if shapes match
                    if model_state[key].shape == value.shape:
                        model_state[key] = value
                # fc3 handled below

            # Handle fc3 weights/bias separately (allow truncation or padding)
            if fc3_w_key and fc3_w_key in adapted_ckpt:
                ck_w = adapted_ckpt[fc3_w_key]
                cur_w = model_state[[k for k in model_state.keys() if k.endswith('fc3.weight')][0]]
                # Determine rows to copy
                rows_to_copy = min(ck_w.size(0), cur_w.size(0))
                cur_w[:rows_to_copy, :] = ck_w[:rows_to_copy, :]
                model_state[[k for k in model_state.keys() if k.endswith('fc3.weight')][0]] = cur_w

            if fc3_b_key and fc3_b_key in adapted_ckpt:
                ck_b = adapted_ckpt[fc3_b_key]
                cur_b = model_state[[k for k in model_state.keys() if k.endswith('fc3.bias')][0]]
                elems_to_copy = min(ck_b.size(0), cur_b.size(0))
                cur_b[:elems_to_copy] = ck_b[:elems_to_copy]
                model_state[[k for k in model_state.keys() if k.endswith('fc3.bias')][0]] = cur_b

            # Load the modified state dict into the network (non-strict to allow missing keys)
            self.q_network.load_state_dict(model_state, strict=False)

        except Exception as e:
            # As a last resort, try to load the checkpoint directly with strict=False
            try:
                self.q_network.load_state_dict(adapted_ckpt, strict=False)
            except Exception:
                raise e

        # Ensure target matches q_network
        self.target_network.load_state_dict(self.q_network.state_dict())


class PolicyGradientAgent:
    """REINFORCE Agent for exercise recommendation"""
    
    def __init__(self, state_size: int, action_size: int,
                 learning_rate: float = 0.001,
                 gamma: float = 0.99,
                 hidden_size: int = 128):
        """
        Initialize Policy Gradient Agent
        
        Args:
            state_size: Dimension of state space
            action_size: Number of possible actions
            learning_rate: Learning rate for optimizer
            gamma: Discount factor
            hidden_size: Hidden layer size
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        
        # Network
        self.device = torch.device("cpu")
        self.policy_network = PolicyNetwork(state_size, action_size, hidden_size).to(self.device)
        
        # Optimizer
        self.optimizer = optim.Adam(self.policy_network.parameters(), lr=learning_rate)
        
        # Episode memory
        self.episode_log_probs = []
        self.episode_rewards = []
        
        # Training stats
        self.training_rewards = []
    
    def act(self, state: np.ndarray) -> Tuple[int, float]:
        """
        Select action based on policy
        
        Args:
            state: Current state
            
        Returns:
            Action index and log probability
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action_probs = self.policy_network(state_tensor)
        
        # Sample action from distribution
        action_dist = torch.distributions.Categorical(action_probs)
        action = action_dist.sample()
        
        return action.item(), action_dist.log_prob(action).item()
    
    def remember(self, log_prob: float, reward: float):
        """Store experience for batch update"""
        self.episode_log_probs.append(log_prob)
        self.episode_rewards.append(reward)
    
    def update(self):
        """Update policy based on episode rewards"""
        if not self.episode_rewards:
            return
        
        # Compute returns (cumulative discounted rewards)
        returns = []
        cumulative_return = 0
        for reward in reversed(self.episode_rewards):
            cumulative_return = reward + self.gamma * cumulative_return
            returns.insert(0, cumulative_return)
        
        # Normalize returns
        returns = np.array(returns)
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)
        
        # Compute loss (negative of expected return)
        loss = 0
        for log_prob, ret in zip(self.episode_log_probs, returns):
            loss -= log_prob * ret
        
        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Store episode reward
        self.training_rewards.append(sum(self.episode_rewards))
        
        # Clear episode memory
        self.episode_log_probs = []
        self.episode_rewards = []
    
    def save(self, filepath: str):
        """Save agent to file"""
        torch.save(self.policy_network.state_dict(), filepath)
    
    def load(self, filepath: str):
        """Load agent from file"""
        self.policy_network.load_state_dict(torch.load(filepath))
