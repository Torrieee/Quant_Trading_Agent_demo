"""
强化学习交易环境

实现符合Gym接口的交易环境，用于训练RL Agent。
"""

from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from .features import add_daily_returns, add_moving_averages, add_zscore


class TradingEnv(gym.Env):
    """
    交易环境
    
    状态空间：技术指标特征
    动作空间：0=空仓, 1=满仓（可扩展为连续动作空间）
    奖励：基于收益和风险调整
    """
    
    metadata = {"render_modes": ["human"], "render_fps": 4}
    
    def __init__(
        self,
        df: pd.DataFrame,
        initial_cash: float = 100000.0,
        fee_rate: float = 0.0005,
        max_position: float = 1.0,
        lookback_window: int = 20,
        reward_type: str = "sharpe",  # "return", "sharpe", "risk_adjusted"
        render_mode: Optional[str] = None,
    ):
        """
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV数据的DataFrame，必须包含Close列
        initial_cash : float
            初始资金
        fee_rate : float
            手续费率
        max_position : float
            最大仓位比例
        lookback_window : int
            回看窗口长度（用于特征计算）
        reward_type : str
            奖励类型：'return', 'sharpe', 'risk_adjusted'
        render_mode : str
            渲染模式
        """
        super().__init__()
        
        self.df = df.copy()
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate
        self.max_position = max_position
        self.lookback_window = lookback_window
        self.reward_type = reward_type
        
        # 准备特征
        self._prepare_features()
        
        # 环境参数
        self.current_step = 0
        self.cash = initial_cash
        self.position = 0.0  # 当前仓位比例
        self.equity = initial_cash
        self.trades = []  # 交易记录
        
        # 动作空间：0=空仓, 1=满仓（可扩展为多档位或连续）
        self.action_space = spaces.Discrete(2)
        
        # 状态空间：技术指标特征
        # 特征包括：价格归一化、收益率、移动平均、z-score等
        n_features = self._get_state_size()
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(n_features,), dtype=np.float32
        )
        
        self.render_mode = render_mode
    
    def _prepare_features(self):
        """准备技术指标特征"""
        df = self.df.copy()
        
        # 添加基础特征
        df = add_daily_returns(df)
        df = add_moving_averages(df, windows=[5, 10, 20, 60])
        df = add_zscore(df, window=self.lookback_window)
        
        # 计算更多技术指标
        df["rsi"] = self._calculate_rsi(df["Close"], window=14)
        df["macd"], df["macd_signal"] = self._calculate_macd(df["Close"])
        
        # 价格归一化（相对于最近N天的价格范围）
        df["price_norm"] = (df["Close"] - df["Close"].rolling(self.lookback_window).min()) / (
            df["Close"].rolling(self.lookback_window).max() - df["Close"].rolling(self.lookback_window).min() + 1e-8
        )
        
        # 波动率
        df["volatility"] = df["ret"].rolling(self.lookback_window).std()
        
        self.df = df.bfill().fillna(0)
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(
        self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series]:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def _get_state_size(self) -> int:
        """计算状态空间大小"""
        # 特征包括：
        # 1. 价格归一化
        # 2. 收益率（最近N天）
        # 3. 移动平均（5, 10, 20, 60天）
        # 4. z-score
        # 5. RSI
        # 6. MACD, MACD Signal
        # 7. 波动率
        # 8. 当前仓位
        # 9. 当前权益（归一化）
        return 1 + self.lookback_window + 4 + 1 + 2 + 1 + 1 + 1  # 约30+个特征
    
    def _get_state(self) -> np.ndarray:
        """获取当前状态"""
        if self.current_step < self.lookback_window:
            # 如果数据不足，返回零向量
            return np.zeros(self.observation_space.shape, dtype=np.float32)
        
        row = self.df.iloc[self.current_step]
        prev_rows = self.df.iloc[max(0, self.current_step - self.lookback_window):self.current_step]
        
        features = []
        
        # 1. 价格归一化
        features.append(row["price_norm"] if not pd.isna(row["price_norm"]) else 0.0)
        
        # 2. 最近N天的收益率
        recent_returns = prev_rows["ret"].values[-self.lookback_window:]
        if len(recent_returns) < self.lookback_window:
            recent_returns = np.pad(
                recent_returns, (self.lookback_window - len(recent_returns), 0), "constant"
            )
        features.extend(recent_returns)
        
        # 3. 移动平均（归一化）
        for window in [5, 10, 20, 60]:
            ma_col = f"ma_{window}"
            if ma_col in row and not pd.isna(row[ma_col]):
                ma_norm = (row["Close"] - row[ma_col]) / (row["Close"] + 1e-8)
                features.append(ma_norm)
            else:
                features.append(0.0)
        
        # 4. z-score
        features.append(row["zscore"] if not pd.isna(row["zscore"]) else 0.0)
        
        # 5. RSI（归一化到0-1）
        features.append((row["rsi"] / 100.0) if not pd.isna(row["rsi"]) else 0.5)
        
        # 6. MACD, MACD Signal（归一化）
        if not pd.isna(row["macd"]):
            features.append(row["macd"] / (row["Close"] + 1e-8))
        else:
            features.append(0.0)
        if not pd.isna(row["macd_signal"]):
            features.append(row["macd_signal"] / (row["Close"] + 1e-8))
        else:
            features.append(0.0)
        
        # 7. 波动率
        features.append(row["volatility"] if not pd.isna(row["volatility"]) else 0.0)
        
        # 8. 当前仓位
        features.append(self.position)
        
        # 9. 当前权益（归一化）
        features.append(self.equity / self.initial_cash)
        
        return np.array(features, dtype=np.float32)
    
    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """重置环境"""
        super().reset(seed=seed)
        
        self.current_step = self.lookback_window  # 从有足够数据的地方开始
        self.cash = self.initial_cash
        self.position = 0.0
        self.equity = self.initial_cash
        self.trades = []
        
        state = self._get_state()
        info = {"equity": self.equity, "step": self.current_step}
        
        return state, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        执行一步
        
        Parameters:
        -----------
        action : int
            0=空仓, 1=满仓
        
        Returns:
        --------
        state : np.ndarray
            新状态
        reward : float
            奖励
        terminated : bool
            是否终止
        truncated : bool
            是否截断
        info : dict
            额外信息
        """
        if self.current_step >= len(self.df) - 1:
            # 已经到达最后一步
            state = self._get_state()
            reward = 0.0
            terminated = True
            truncated = False
            info = {"equity": self.equity, "step": self.current_step}
            return state, reward, terminated, truncated, info
        
        # 获取当前价格和收益率
        current_row = self.df.iloc[self.current_step]
        next_row = self.df.iloc[self.current_step + 1]
        current_price = current_row["Close"]
        next_price = next_row["Close"]
        return_rate = next_row["ret"]
        
        # 执行动作：调整仓位
        target_position = float(action) * self.max_position
        position_change = target_position - self.position
        
        # 计算手续费
        fee = abs(position_change) * self.equity * self.fee_rate
        
        # 更新仓位
        self.position = target_position
        
        # 计算收益
        gross_return = self.position * return_rate
        net_return = gross_return - (fee / self.equity) if self.equity > 0 else 0
        
        # 更新权益
        self.equity = self.equity * (1 + net_return)
        self.cash = self.equity * (1 - self.position)
        
        # 记录交易和收益
        if abs(position_change) > 0.01:  # 仓位变化超过1%才记录
            self.trades.append({
                "step": self.current_step,
                "action": action,
                "price": current_price,
                "position": self.position,
                "equity": self.equity,
                "return": net_return,
            })
        
        # 移动到下一步
        self.current_step += 1
        
        # 计算奖励
        reward = self._calculate_reward(net_return)
        
        # 检查是否终止
        terminated = self.current_step >= len(self.df) - 1
        truncated = False
        
        # 获取新状态
        state = self._get_state()
        
        info = {
            "equity": self.equity,
            "position": self.position,
            "step": self.current_step,
            "return": net_return,
        }
        
        return state, reward, terminated, truncated, info
    
    def _calculate_reward(self, return_rate: float) -> float:
        """计算奖励"""
        if self.reward_type == "return":
            # 简单收益奖励
            return return_rate * 100  # 放大奖励便于学习
        
        elif self.reward_type == "sharpe":
            # 基于夏普比率的奖励（需要历史收益）
            if len(self.trades) < 2:
                return return_rate * 100
            
            # 计算最近N步的收益
            recent_returns = [t.get("return", 0) for t in self.trades[-20:]]
            if len(recent_returns) > 1:
                mean_ret = np.mean(recent_returns)
                std_ret = np.std(recent_returns) + 1e-8
                sharpe = mean_ret / std_ret * np.sqrt(252)  # 年化夏普
                return sharpe * 10  # 放大
            return return_rate * 100
        
        elif self.reward_type == "risk_adjusted":
            # 风险调整收益：收益 - 风险惩罚
            risk_penalty = abs(return_rate) * 0.5  # 波动惩罚
            return (return_rate - risk_penalty) * 100
        
        else:
            return return_rate * 100
    
    def render(self):
        """渲染环境（可选）"""
        if self.render_mode == "human":
            print(f"Step: {self.current_step}, Equity: {self.equity:.2f}, Position: {self.position:.2%}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取环境统计信息"""
        total_return = (self.equity / self.initial_cash - 1) if self.initial_cash > 0 else 0.0
        num_trades = len(self.trades)
        
        return {
            "total_return": total_return,
            "final_equity": self.equity,
            "num_trades": num_trades,
        }


__all__ = ["TradingEnv"]

