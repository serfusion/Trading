# T-XAU: Gold Trading Bot Using Reinforcement Learning

## Overview

**T-XAU** is a reinforcement learning-based trading bot designed to trade gold (XAU) using historical price data. The bot leverages the PPO (Proximal Policy Optimization) algorithm from the `stable-baselines3` library to learn and execute profitable trading strategies. The project includes a custom trading environment, backtesting, and evaluation tools.

---

## Features

- **Custom Trading Environment:** Simulates gold trading with realistic constraints.
- **Reinforcement Learning:** Uses PPO for training and decision-making.
- **Backtesting:** Evaluate performance on historical test datasets.
- **Metrics:** Tracks profit, balance changes, and overall trading performance.

---

## Project Structure

```
.
├── CollectData.py           # Script to collect gold price data
├── README.md                # Project documentation
├── __pycache__              # Compiled Python files
├── data
│   ├── gold_prices.csv      # Training dataset
│   └── test_gold_prices.csv # Testing dataset
├── environment.py           # Custom trading environment
├── main.py                  # Script to train the trading model
├── models
│   └── ppo_gold_trader.zip  # Trained PPO model
├── ppo_trading              # TensorBoard logs for training
├── test
│   └── test_model.py        # Script to evaluate the trained model
```

---

## Requirements

Ensure the following dependencies are installed before running the project:

- Python 3.10+
- `numpy`
- `pandas`
- `stable-baselines3`
- `tensorflow`
- `gym`
- `matplotlib`

You can install them using:
```bash
pip install -r requirements.txt
```

---

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/T-XAU.git
   cd T-XAU
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Organize your datasets:
   - Place training data in `data/gold_prices.csv`.
   - Place test data in `data/test_gold_prices.csv`.

---

## Usage

### Training the Model
Run the following command to train the model using PPO:
```bash
python3 main.py
```

### Evaluating the Model
Use the `test_model.py` script to evaluate the trained model on test data:
```bash
python3 test/test_model.py
```

### Viewing Training Logs
Monitor training progress using TensorBoard:
```bash
tensorboard --logdir=ppo_trading
```

---

## Results

- Initial Balance: $10,000  
- Final Balance: (Displayed after running `test_model.py`)  
- Total Profit: (Displayed after running `test_model.py`)  
- Profit Percentage: (Displayed after running `test_model.py`)  

---

## Contributing

Contributions are welcome! If you'd like to contribute:
1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Commit your changes and push to your fork.
4. Submit a pull request with a clear description of your work.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Author

Developed by **Wael Slimi**.  
Contact: [slimiwael@proton.me](mailto:slimiwael@proton.me)  
LinkedIn: [linkedin.com/in/wael-slimi](https://www.linkedin.com/in/wael-slimi-1944161a4/)

