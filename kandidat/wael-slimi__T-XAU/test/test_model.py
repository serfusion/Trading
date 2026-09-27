import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from environment import TradingEnv
from stable_baselines3.common.vec_env import DummyVecEnv

def load_test_data(filepath):
    data = pd.read_csv(filepath)
    numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors='coerce')
    data = data.dropna(subset=numeric_columns)
    data = data[numeric_columns]
    return data.reset_index(drop=True)

def evaluate_model(model_path, test_data, initial_balance=10000):
    env = DummyVecEnv([lambda: TradingEnv(test_data, initial_balance=initial_balance)])
    
    model = PPO.load(model_path, env=env)
    
    obs = env.reset()
    done = False
    total_reward = 0
    steps = 0
    
    while not done:
        action, _ = model.predict(obs)
        obs, reward, done, info = env.step(action)
        total_reward += reward[0]
        steps += 1
    
    final_balance = initial_balance + total_reward
    return {
        'Initial Balance': initial_balance,
        'Final Balance': final_balance,
        'Total Profit': final_balance - initial_balance,
        'Profit Percentage': ((final_balance - initial_balance) / initial_balance) * 100,
        'Total Steps': steps
    }

def main():
    model_path = "/home/zven/Gl3/project/T-XAU/models/ppo_gold_trader.zip"
    test_data_path = "/home/zven/Gl3/project/T-XAU/data/test_gold_prices.csv"
    
    test_data = load_test_data(test_data_path)
    
    results = evaluate_model(model_path, test_data)
    
    print("\n--- Model Performance Evaluation ---")
    for key, value in results.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()