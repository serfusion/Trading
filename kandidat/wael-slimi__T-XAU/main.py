from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from environment import TradingEnv
import pandas as pd 
import os 

os.makedirs("modes",exist_ok= True)
data = pd.read_csv('/home/zven/Gl3/project/T-XAU/data/gold_prices.csv')

numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors='coerce')
data = data.dropna(subset=numeric_columns)

data = data[numeric_columns]
data = data.reset_index(drop=True)

env = DummyVecEnv([lambda: TradingEnv(data, initial_balance=10000)])

model = PPO('MlpPolicy',env , verbose= 1, tensorboard_log="./ppo_trading")
model.learn(total_timesteps=100000)
model.save("models/ppo_gold_trader")
