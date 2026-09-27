import gym
import numpy as np
import pandas as pd
from gym import spaces

class TradingEnv(gym.Env):
    def __init__(self, data, initial_balance=10000):
        super(TradingEnv, self).__init__()
        self.data = data
        self.initial_balance = initial_balance
        self.current_step = 0
        self.balance = initial_balance
        self.positions = 0
        self.total_profit = 0
        self.observation_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Define action and observation space
        self.action_space = spaces.Discrete(3)  # 0: sell, 1: hold, 2: buy
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(len(self.observation_columns),), dtype=np.float32
        )

    def reset(self):
        self.current_step = 0
        self.balance = self.initial_balance
        self.positions = 0
        self.total_profit = 0
        return self._next_observation()

    def step(self, action):
        current_price = self.data.iloc[self.current_step]['Close']
        reward = 0

        if action == 0:  # Sell
            self.balance += self.positions * current_price
            self.positions = 0
        elif action == 2:  # Buy
            self.positions += self.balance / current_price
            self.balance = 0

        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        if done:
            reward = self.balance + self.positions * current_price - self.initial_balance

        return self._next_observation(), reward, done, {}

    def _next_observation(self):
        # Return only the selected columns as the observation
        return self.data.iloc[self.current_step].values

    def render(self, mode='human'):
        profit = self.balance + self.positions * self.data.iloc[self.current_step]['Close'] - self.initial_balance
        print(f"Step: {self.current_step}, Balance: {self.balance}, Positions: {self.positions}, Profit: {profit}")