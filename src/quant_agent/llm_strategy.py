"""
LLM驱动的策略生成和解释模块

利用大模型的自然语言理解和生成能力，实现：
1. 自然语言策略生成
2. 策略解释和分析
3. 智能策略组合推荐
"""

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. LLM strategy features will not work.")


class LLMStrategyGenerator:
    """使用LLM从自然语言描述生成策略"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required. Install with: pip install openai")
        
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model
    
    def generate_strategy_from_description(
        self,
        description: str,
        symbol: str = "AAPL",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        根据自然语言描述生成交易策略
        
        Parameters:
        -----------
        description : str
            策略描述，例如："当价格低于20日均线时买入，高于时卖出"
        symbol : str
            股票代码
        context : dict
            上下文信息（市场状态、历史表现等）
        
        Returns:
        --------
        dict
            生成的策略配置和代码
        """
        if not self.client:
            return {"error": "OpenAI client not initialized"}
        
        # 构建提示词
        prompt = f"""
作为量化交易专家，请根据以下描述生成一个交易策略。

策略描述：{description}
股票代码：{symbol}

请生成：
1. 策略名称（简洁明了）
2. 策略逻辑（详细说明）
3. 参数配置（如果有）
4. 适用市场状态（趋势市/震荡市等）
5. 风险提示

格式要求：
- 策略名称：一个简短的名称
- 策略逻辑：详细说明买入和卖出条件
- 参数：如果有技术指标，说明参数值
- 适用场景：说明在什么市场状态下使用
- 风险提示：说明可能的风险

请以JSON格式返回，包含以下字段：
{{
    "strategy_name": "...",
    "logic": "...",
    "parameters": {{}},
    "suitable_market": "...",
    "risk_warning": "..."
}}
"""
        
        if context:
            prompt += f"\n\n上下文信息：{context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的量化交易策略分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content
            
            # 尝试解析JSON（LLM可能返回markdown格式）
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # 如果无法解析JSON，返回文本
                result = {
                    "strategy_name": "LLM生成策略",
                    "logic": result_text,
                    "parameters": {},
                    "suitable_market": "未知",
                    "risk_warning": "请谨慎使用"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating strategy: {e}")
            return {"error": str(e)}
    
    def generate_strategy_code(
        self,
        strategy_description: Dict[str, Any],
        template: Optional[str] = None
    ) -> str:
        """
        根据策略描述生成Python代码
        
        Parameters:
        -----------
        strategy_description : dict
            策略描述（来自generate_strategy_from_description）
        template : str
            代码模板（可选）
        
        Returns:
        --------
        str
            生成的策略代码
        """
        if not self.client:
            return "# Error: OpenAI client not initialized"
        
        prompt = f"""
根据以下策略描述，生成Python函数代码来实现这个交易策略。

策略信息：
- 名称：{strategy_description.get('strategy_name', 'Unknown')}
- 逻辑：{strategy_description.get('logic', '')}
- 参数：{strategy_description.get('parameters', {})}

要求：
1. 函数签名：def generate_signals(df: pd.DataFrame, params: dict) -> pd.Series
2. 输入：DataFrame包含OHLCV数据和技术指标
3. 输出：Series，值为0（空仓）或1（满仓）
4. 使用pandas和numpy
5. 代码要有注释

示例代码结构：
```python
def generate_signals(df: pd.DataFrame, params: dict) -> pd.Series:
    \"\"\"
    生成交易信号
    
    Parameters:
    -----------
    df : pd.DataFrame
        包含OHLCV和技术指标的DataFrame
    params : dict
        策略参数
    
    Returns:
    --------
    pd.Series
        交易信号（0或1）
    \"\"\"
    signals = pd.Series(0, index=df.index)
    
    # 在这里实现策略逻辑
    # ...
    
    return signals
```

请只返回Python代码，不要包含markdown格式。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的Python量化交易代码生成器。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # 降低温度，生成更准确的代码
            )
            
            code = response.choices[0].message.content
            
            # 清理代码（移除markdown标记）
            code = re.sub(r'```python\n?', '', code)
            code = re.sub(r'```\n?', '', code)
            code = code.strip()
            
            return code
            
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return f"# Error: {str(e)}"


class LLMStrategyExplainer:
    """使用LLM解释策略逻辑和表现"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required. Install with: pip install openai")
        
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model
    
    def explain_strategy_logic(
        self,
        strategy_name: str,
        strategy_code: Optional[str] = None,
        strategy_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        解释策略逻辑
        
        Parameters:
        -----------
        strategy_name : str
            策略名称
        strategy_code : str
            策略代码（可选）
        strategy_config : dict
            策略配置（可选）
        
        Returns:
        --------
        str
            策略解释
        """
        if not self.client:
            return "Error: OpenAI client not initialized"
        
        prompt = f"""
请解释以下交易策略的逻辑和工作原理。

策略名称：{strategy_name}
"""
        
        if strategy_code:
            prompt += f"\n策略代码：\n```python\n{strategy_code}\n```"
        
        if strategy_config:
            prompt += f"\n策略配置：{strategy_config}"
        
        prompt += """

请提供：
1. 策略的核心思想（1-2句话）
2. 买入条件（详细说明）
3. 卖出条件（详细说明）
4. 适用场景（什么市场状态下使用）
5. 优缺点分析

请用通俗易懂的语言解释，适合非专业人士理解。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的量化交易策略分析师，擅长用通俗易懂的语言解释复杂的策略。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error explaining strategy: {e}")
            return f"Error: {str(e)}"
    
    def analyze_strategy_performance(
        self,
        strategy_name: str,
        backtest_results: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        分析策略表现
        
        Parameters:
        -----------
        strategy_name : str
            策略名称
        backtest_results : dict
            回测结果（包含收益率、夏普比率、最大回撤等）
        market_context : dict
            市场环境信息（可选）
        
        Returns:
        --------
        str
            策略表现分析
        """
        if not self.client:
            return "Error: OpenAI client not initialized"
        
        prompt = f"""
作为量化交易专家，请分析以下策略的回测表现。

策略名称：{strategy_name}

回测结果：
- 总收益率：{backtest_results.get('total_return', 0):.2%}
- 年化收益率：{backtest_results.get('annual_return', 0):.2%}
- 夏普比率：{backtest_results.get('sharpe', 0):.4f}
- 最大回撤：{backtest_results.get('max_drawdown', 0):.2%}
- 年化波动率：{backtest_results.get('annual_volatility', 0):.2%}
"""
        
        if market_context:
            prompt += f"\n市场环境：{market_context}"
        
        prompt += """

请提供：
1. 整体评价（表现如何）
2. 收益分析（收益率是否合理）
3. 风险分析（回撤和波动率是否可控）
4. 改进建议（如何优化策略）
5. 适用性评估（是否适合当前市场）

请用专业但易懂的语言分析。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的量化交易策略分析师，擅长分析策略表现和提供改进建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return f"Error: {str(e)}"


class LLMStrategyAdvisor:
    """使用LLM推荐策略组合"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required. Install with: pip install openai")
        
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model
    
    def recommend_strategy_portfolio(
        self,
        market_state: str,
        risk_tolerance: str = "medium",
        available_strategies: Optional[List[str]] = None,
        historical_performance: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        推荐策略组合
        
        Parameters:
        -----------
        market_state : str
            市场状态（trending_up, trending_down, ranging等）
        risk_tolerance : str
            风险承受能力（low, medium, high）
        available_strategies : list
            可用策略列表
        historical_performance : dict
            历史表现数据
        
        Returns:
        --------
        dict
            推荐的策略组合
        """
        if not self.client:
            return {"error": "OpenAI client not initialized"}
        
        if available_strategies is None:
            available_strategies = ["mean_reversion", "momentum"]
        
        prompt = f"""
作为量化交易组合管理专家，请根据以下信息推荐策略组合。

市场状态：{market_state}
风险承受能力：{risk_tolerance}
可用策略：{', '.join(available_strategies)}
"""
        
        if historical_performance:
            prompt += "\n历史表现：\n"
            for strategy, perf in historical_performance.items():
                prompt += f"- {strategy}: 年化收益{perf.get('annual_return', 0):.2%}, 夏普{perf.get('sharpe', 0):.4f}\n"
        
        prompt += """

请推荐：
1. 策略组合（选择哪些策略，各占多少权重）
2. 推荐理由（为什么这样组合）
3. 预期表现（预期收益率和风险）
4. 风险提示（需要注意什么）

请以JSON格式返回：
{{
    "recommended_strategies": [
        {{"name": "...", "weight": 0.5, "reason": "..."}},
        ...
    ],
    "expected_return": 0.15,
    "expected_risk": 0.12,
    "risk_warning": "..."
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的量化交易组合管理专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content
            
            # 解析JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "recommended_strategies": [
                        {"name": available_strategies[0], "weight": 1.0, "reason": "基于市场状态推荐"}
                    ],
                    "expected_return": 0.15,
                    "expected_risk": 0.12,
                    "risk_warning": "请谨慎使用"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error recommending portfolio: {e}")
            return {"error": str(e)}
    
    def suggest_strategy_improvement(
        self,
        strategy_name: str,
        current_performance: Dict[str, Any],
        market_conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        建议策略改进
        
        Parameters:
        -----------
        strategy_name : str
            策略名称
        current_performance : dict
            当前表现
        market_conditions : dict
            市场条件
        
        Returns:
        --------
        str
            改进建议
        """
        if not self.client:
            return "Error: OpenAI client not initialized"
        
        prompt = f"""
作为量化交易策略优化专家，请分析以下策略并提供改进建议。

策略名称：{strategy_name}

当前表现：
- 年化收益率：{current_performance.get('annual_return', 0):.2%}
- 夏普比率：{current_performance.get('sharpe', 0):.4f}
- 最大回撤：{current_performance.get('max_drawdown', 0):.2%}
"""
        
        if market_conditions:
            prompt += f"\n市场条件：{market_conditions}"
        
        prompt += """

请提供：
1. 问题诊断（策略存在什么问题）
2. 改进方向（如何优化）
3. 具体建议（参数调整、条件优化等）
4. 预期效果（改进后预期表现）

请提供具体可执行的建议。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的量化交易策略优化专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error suggesting improvement: {e}")
            return f"Error: {str(e)}"


__all__ = [
    "LLMStrategyGenerator",
    "LLMStrategyExplainer",
    "LLMStrategyAdvisor",
]

