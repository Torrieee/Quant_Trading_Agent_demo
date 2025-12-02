"""
强化学习训练模块

使用Stable-Baselines3训练RL Agent
"""

from typing import Dict, Optional, Tuple

import numpy as np
from loguru import logger

from .data import DataConfig, download_ohlcv
from .rl_env import TradingEnv

try:
    from stable_baselines3 import PPO, A2C, DQN, SAC, TD3
    from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv
    STABLE_BASELINES3_AVAILABLE = True
except ImportError:
    STABLE_BASELINES3_AVAILABLE = False
    logger.warning("stable-baselines3 not installed. RL training will not work.")


class TradingCallback(BaseCallback):
    """训练回调，记录训练过程"""
    
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
    
    def _on_step(self) -> bool:
        return True


def create_trading_env(
    data_cfg: DataConfig,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0005,
    max_position: float = 1.0,
    reward_type: str = "sharpe",
) -> TradingEnv:
    """
    创建交易环境
    
    Parameters:
    -----------
    data_cfg : DataConfig
        数据配置
    initial_cash : float
        初始资金
    fee_rate : float
        手续费率
    max_position : float
        最大仓位
    reward_type : str
        奖励类型
    
    Returns:
    --------
    TradingEnv
        交易环境
    """
    # 下载数据
    df = download_ohlcv(data_cfg, use_cache=True)
    
    # 创建环境
    env = TradingEnv(
        df=df,
        initial_cash=initial_cash,
        fee_rate=fee_rate,
        max_position=max_position,
        reward_type=reward_type,
    )
    
    return env


def train_rl_agent(
    data_cfg: DataConfig,
    algorithm: str = "PPO",
    total_timesteps: int = 100000,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0005,
    max_position: float = 1.0,
    reward_type: str = "sharpe",
    model_save_path: Optional[str] = None,
    eval_data_cfg: Optional[DataConfig] = None,
    verbose: int = 1,
) -> Tuple[Any, Dict]:
    """
    训练RL Agent
    
    Parameters:
    -----------
    data_cfg : DataConfig
        训练数据配置
    algorithm : str
        算法名称：'PPO', 'A2C', 'DQN', 'SAC', 'TD3'
    total_timesteps : int
        总训练步数
    initial_cash : float
        初始资金
    fee_rate : float
        手续费率
    max_position : float
        最大仓位
    reward_type : str
        奖励类型
    model_save_path : str
        模型保存路径
    eval_data_cfg : DataConfig
        评估数据配置（用于验证）
    verbose : int
        日志详细程度
    
    Returns:
    --------
    model : Any
        训练好的模型
    training_info : dict
        训练信息
    """
    if not STABLE_BASELINES3_AVAILABLE:
        raise ImportError(
            "stable-baselines3 is required for RL training. "
            "Install it with: pip install stable-baselines3[extra]"
        )
    
    logger.info(f"Creating training environment for {data_cfg.symbol}")
    
    # 创建训练环境
    train_env = create_trading_env(
        data_cfg=data_cfg,
        initial_cash=initial_cash,
        fee_rate=fee_rate,
        max_position=max_position,
        reward_type=reward_type,
    )
    train_env = Monitor(train_env)
    train_env = DummyVecEnv([lambda: train_env])
    
    # 创建评估环境（如果提供）
    eval_env = None
    if eval_data_cfg:
        logger.info(f"Creating evaluation environment for {eval_data_cfg.symbol}")
        eval_env = create_trading_env(
            data_cfg=eval_data_cfg,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            max_position=max_position,
            reward_type=reward_type,
        )
        eval_env = Monitor(eval_env)
        eval_env = DummyVecEnv([lambda: eval_env])
    
    # 选择算法
    algorithm_map = {
        "PPO": PPO,
        "A2C": A2C,
        "DQN": DQN,
        "SAC": SAC,
        "TD3": TD3,
    }
    
    if algorithm not in algorithm_map:
        raise ValueError(f"Unknown algorithm: {algorithm}. Choose from {list(algorithm_map.keys())}")
    
    ModelClass = algorithm_map[algorithm]
    
    # 创建模型
    logger.info(f"Creating {algorithm} model...")
    model = ModelClass(
        "MlpPolicy",
        train_env,
        verbose=verbose,
        tensorboard_log="./logs/tensorboard/" if model_save_path else None,
    )
    
    # 设置回调
    callbacks = []
    if eval_env:
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=model_save_path.replace(".zip", "_best") if model_save_path else None,
            log_path="./logs/eval/" if model_save_path else None,
            eval_freq=5000,
            deterministic=True,
            render=False,
        )
        callbacks.append(eval_callback)
    
    # 训练
    logger.info(f"Training {algorithm} agent for {total_timesteps} timesteps...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=callbacks if callbacks else None,
        progress_bar=True,
    )
    
    # 保存模型
    if model_save_path:
        logger.info(f"Saving model to {model_save_path}")
        model.save(model_save_path)
    
    # 收集训练信息
    training_info = {
        "algorithm": algorithm,
        "total_timesteps": total_timesteps,
        "data_symbol": data_cfg.symbol,
        "model_path": model_save_path,
    }
    
    return model, training_info


def evaluate_rl_agent(
    model: Any,
    data_cfg: DataConfig,
    initial_cash: float = 100000.0,
    fee_rate: float = 0.0005,
    max_position: float = 1.0,
    num_episodes: int = 1,
) -> Dict:
    """
    评估RL Agent
    
    Parameters:
    -----------
    model : Any
        训练好的模型
    data_cfg : DataConfig
        评估数据配置
    initial_cash : float
        初始资金
    fee_rate : float
        手续费率
    max_position : float
        最大仓位
    num_episodes : int
        评估回合数
    
    Returns:
    --------
    dict
        评估结果
    """
    env = create_trading_env(
        data_cfg=data_cfg,
        initial_cash=initial_cash,
        fee_rate=fee_rate,
        max_position=max_position,
    )
    
    episode_returns = []
    episode_lengths = []
    
    for episode in range(num_episodes):
        obs, info = env.reset()
        done = False
        episode_return = 0.0
        episode_length = 0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_return += reward
            episode_length += 1
        
        stats = env.get_stats()
        episode_returns.append(stats["total_return"])
        episode_lengths.append(episode_length)
    
    # 计算统计信息
    mean_return = np.mean(episode_returns)
    std_return = np.std(episode_returns)
    
    return {
        "mean_return": mean_return,
        "std_return": std_return,
        "episode_returns": episode_returns,
        "episode_lengths": episode_lengths,
        "num_episodes": num_episodes,
    }


__all__ = [
    "create_trading_env",
    "train_rl_agent",
    "evaluate_rl_agent",
    "TradingCallback",
]

