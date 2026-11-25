"""
RL Agent for Exercise Recommendation
Implements Deep Q-Network (DQN) and Policy Gradient (REINFORCE) agents
with device-safe and shape-safe checkpoint loading.
"""

from typing import Tuple
from collections import deque
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class QNetwork(nn.Module):
    """Deep Q-Network for continuous state approximation."""

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        self.relu = nn.ReLU()

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        return self.fc3(x)


class PolicyNetwork(nn.Module):
    """Policy Network for Policy Gradient methods."""

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super(PolicyNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        return self.softmax(self.fc3(x))


class DQNAgent:
    """Deep Q-Network Agent for exercise recommendation."""

    def __init__(
        self,
        state_size: int,
        action_size: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        hidden_size: int = 128
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_network = QNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_network = QNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())

        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()

        self.memory = deque(maxlen=10000)
        self.batch_size = 32

        self.training_rewards = []
        self.training_losses = []

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool
    ):
        """Store transition experience in replay buffer."""
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state: np.ndarray) -> int:
        """Select action using epsilon-greedy strategy."""
        if np.random.random() < self.epsilon:
            return int(np.random.randint(self.action_size))

        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor)

        return int(q_values.argmax(dim=1).item())

    def replay(self, batch_size: int):
        """Train on mini-batch sampled from experience replay."""
        if len(self.memory) < batch_size:
            return

        batch = np.random.choice(len(self.memory), batch_size, replace=False)
        states, actions, rewards, next_states, dones = zip(
            *[self.memory[i] for i in batch]
        )

        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)

        q_values = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(dim=1)[0]
            target_q_values = rewards + self.gamma * next_q_values * (1.0 - dones)

        loss = self.criterion(q_values, target_q_values)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()

        self.training_losses.append(loss.item())

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def update_target_network(self):
        """Synchronize target network weights with primary Q-network."""
        self.target_network.load_state_dict(self.q_network.state_dict())

    def save(self, filepath: str):
        """Save Q-network weights to file."""
        torch.save(self.q_network.state_dict(), filepath)

    def load(self, filepath: str):
        """
        Load Q-network weights from file safely, adapting output layer shapes
        if the exercise database size changed since training.
        """
        checkpoint = torch.load(filepath, map_location=self.device, weights_only=True)

        adapted_ckpt = {}
        for k, v in checkpoint.items():
            name = k[len('module.'):] if k.startswith('module.') else k
            adapted_ckpt[name] = v

        model_state = self.q_network.state_dict()
        fc3_w_key = next((k for k in adapted_ckpt if k.endswith('fc3.weight')), None)
        fc3_b_key = next((k for k in adapted_ckpt if k.endswith('fc3.bias')), None)

        for key, value in adapted_ckpt.items():
            if key in model_state and key not in (fc3_w_key, fc3_b_key):
                if model_state[key].shape == value.shape:
                    model_state[key] = value

        if fc3_w_key and fc3_w_key in adapted_ckpt:
            ck_w = adapted_ckpt[fc3_w_key]
            target_w_key = next(k for k in model_state if k.endswith('fc3.weight'))
            cur_w = model_state[target_w_key]
            if ck_w.size(1) == cur_w.size(1):
                rows = min(ck_w.size(0), cur_w.size(0))
                cur_w[:rows, :] = ck_w[:rows, :]
                model_state[target_w_key] = cur_w

        if fc3_b_key and fc3_b_key in adapted_ckpt:
            ck_b = adapted_ckpt[fc3_b_key]
            target_b_key = next(k for k in model_state if k.endswith('fc3.bias'))
            cur_b = model_state[target_b_key]
            elems = min(ck_b.size(0), cur_b.size(0))
            cur_b[:elems] = ck_b[:elems]
            model_state[target_b_key] = cur_b

        self.q_network.load_state_dict(model_state, strict=False)
        self.target_network.load_state_dict(self.q_network.state_dict())


class PolicyGradientAgent:
    """REINFORCE Policy Gradient Agent for exercise recommendation."""

    def __init__(
        self,
        state_size: int,
        action_size: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        hidden_size: int = 128
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_network = PolicyNetwork(state_size, action_size, hidden_size).to(self.device)
        self.optimizer = optim.Adam(self.policy_network.parameters(), lr=learning_rate)

        self.episode_log_probs = []
        self.episode_rewards = []
        self.training_rewards = []

    def act(self, state: np.ndarray) -> Tuple[int, torch.Tensor]:
        """Select action stochastically from policy distribution."""
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        action_probs = self.policy_network(state_tensor)
        action_dist = torch.distributions.Categorical(action_probs)
        action = action_dist.sample()
        return int(action.item()), action_dist.log_prob(action)

    def remember(self, log_prob: torch.Tensor, reward: float):
        """Store step log probability and reward for episode update."""
        self.episode_log_probs.append(log_prob)
        self.episode_rewards.append(reward)

    def update(self):
        """Update policy network using normalized discounted returns."""
        if not self.episode_rewards:
            return

        returns = []
        cumulative_return = 0.0
        for reward in reversed(self.episode_rewards):
            cumulative_return = reward + self.gamma * cumulative_return
            returns.insert(0, cumulative_return)

        returns_t = torch.FloatTensor(returns).to(self.device)
        if returns_t.numel() > 1:
            returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-8)

        loss = torch.stack([-lp * ret for lp, ret in zip(self.episode_log_probs, returns_t)]).sum()

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.training_rewards.append(sum(self.episode_rewards))
        self.episode_log_probs = []
        self.episode_rewards = []

    def save(self, filepath: str):
        """Save policy network weights to file."""
        torch.save(self.policy_network.state_dict(), filepath)

    def load(self, filepath: str):
        """Load policy network weights safely onto current device."""
        state_dict = torch.load(filepath, map_location=self.device, weights_only=True)
        self.policy_network.load_state_dict(state_dict, strict=False)