"""
交易工具 Function Calling 模块（供 Harness 与 QuantEngine Research/Risk 使用）。
"""

from typing import Any, Dict, List, Optional

from loguru import logger
class TradingFunctionCaller:
    """交易相关的Function Calling工具"""
    
    def __init__(
        self,
        data_source=None,
        strategy_executor=None,
        llm_strategy_generator=None,
        evidence_retriever=None,
    ):
        self.data_source = data_source
        self.strategy_executor = strategy_executor
        self.llm_strategy_generator = llm_strategy_generator  # 新增：LLM策略生成器
        self.evidence_retriever = evidence_retriever
    
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """返回可用的Function Calling工具列表"""
        functions = [
            {
                "name": "get_market_data",
                "description": "获取指定股票的历史市场数据（OHLCV）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "股票代码，例如 AAPL, MSFT, TSLA"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "开始日期，格式 YYYY-MM-DD"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期，格式 YYYY-MM-DD，可选"
                        }
                    },
                    "required": ["symbol", "start_date"]
                }
            },
            {
                "name": "analyze_market_state",
                "description": "分析当前市场状态（趋势市、震荡市等）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "股票代码"
                        },
                        "lookback_days": {
                            "type": "integer",
                            "description": "回看天数，默认60天",
                            "default": 60
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_strategy_recommendation",
                "description": "根据市场状态与指标对 momentum/mean_reversion 打分并推荐策略",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "股票代码，例如 AAPL"
                        },
                        "market_state": {
                            "type": "string",
                            "description": "市场状态：trending_up, trending_down, ranging, high_volatility, low_volatility",
                            "enum": ["trending_up", "trending_down", "ranging", "high_volatility", "low_volatility"]
                        },
                        "volatility": {
                            "type": "number",
                            "description": "年化波动率（可选，来自 analyze_market_state）"
                        },
                        "trend_strength": {
                            "type": "number",
                            "description": "趋势强度 0-1（可选）"
                        },
                        "is_bullish": {"type": "boolean"},
                        "is_bearish": {"type": "boolean"},
                        "risk_flags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "披露风险标记，如 supply_chain、going_concern"
                        }
                    },
                    "required": ["market_state"]
                }
            },
            {
                "name": "search_evidence",
                "description": "在已索引的公司披露、基本面文档与历次分析记忆（episodic_memory）中检索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "股票代码"
                        },
                        "query": {
                            "type": "string",
                            "description": "检索问题或关键词"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回条数，默认 5",
                            "default": 5
                        },
                        "doc_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "可选文档类型过滤，如 10-K、8-K、profile"
                        }
                    },
                    "required": ["symbol", "query"]
                }
            },
            {
                "name": "calculate_position_size",
                "description": "计算最优仓位大小（使用凯利公式或风险平价）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "计算方法：kelly, risk_parity, volatility_targeting",
                            "enum": ["kelly", "risk_parity", "volatility_targeting"]
                        },
                        "win_rate": {
                            "type": "number",
                            "description": "胜率（0-1），仅用于凯利公式"
                        },
                        "avg_win": {
                            "type": "number",
                            "description": "平均盈利比例，仅用于凯利公式"
                        },
                        "avg_loss": {
                            "type": "number",
                            "description": "平均亏损比例，仅用于凯利公式"
                        },
                        "volatility": {
                            "type": "number",
                            "description": "波动率，用于风险平价和波动率目标"
                        }
                    },
                    "required": ["method"]
                }
            },
            {
                "name": "run_backtest",
                "description": "运行策略回测",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "股票代码"
                        },
                        "strategy": {
                            "type": "string",
                            "description": "策略名称：mean_reversion 或 momentum",
                            "enum": ["mean_reversion", "momentum"]
                        },
                        "start_date": {
                            "type": "string",
                            "description": "开始日期"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期"
                        }
                    },
                    "required": ["symbol", "strategy", "start_date"]
                }
            },
            {
                "name": "submit_paper_order",
                "description": "模拟盘下单（buy/sell）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "side": {"type": "string", "enum": ["buy", "sell"]},
                        "quantity": {"type": "number"},
                        "price": {"type": "number"},
                    },
                    "required": ["symbol", "side", "quantity", "price"],
                },
            },
            {
                "name": "get_paper_portfolio",
                "description": "查询模拟盘持仓与现金",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        ]
        
        # 添加LLM原创功能（如果可用）
        if self.llm_strategy_generator:
            functions.extend([
                {
                    "name": "generate_strategy_from_description",
                    "description": "根据自然语言描述生成交易策略（LLM生成）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "策略描述，例如：'当价格低于20日均线时买入，高于时卖出'"
                            },
                            "symbol": {
                                "type": "string",
                                "description": "股票代码，用于上下文"
                            }
                        },
                        "required": ["description"]
                    }
                },
                {
                    "name": "explain_strategy",
                    "description": "使用自然语言解释策略逻辑和表现（LLM生成）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_name": {
                                "type": "string",
                                "description": "策略名称"
                            },
                            "backtest_results": {
                                "type": "object",
                                "description": "回测结果（包含收益率、夏普比率等）"
                            }
                        },
                        "required": ["strategy_name"]
                    }
                },
                {
                    "name": "recommend_strategy_portfolio",
                    "description": "根据市场状态和风险偏好推荐策略组合（LLM生成）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "market_state": {
                                "type": "string",
                                "description": "市场状态：trending_up, trending_down, ranging等"
                            },
                            "risk_tolerance": {
                                "type": "string",
                                "description": "风险承受能力：low, medium, high",
                                "enum": ["low", "medium", "high"]
                            }
                        },
                        "required": ["market_state", "risk_tolerance"]
                    }
                }
            ])
        
        return functions
    
    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """执行Function Calling"""
        try:
            if function_name == "get_market_data":
                return self._get_market_data(
                    arguments["symbol"],
                    arguments["start_date"],
                    arguments.get("end_date")
                )
            elif function_name == "analyze_market_state":
                return self._analyze_market_state(
                    arguments["symbol"],
                    arguments.get("lookback_days", 60)
                )
            elif function_name == "get_strategy_recommendation":
                return self._get_strategy_recommendation(arguments)
            elif function_name == "search_evidence":
                return self._search_evidence(arguments)
            elif function_name == "calculate_position_size":
                return self._calculate_position_size(arguments)
            elif function_name == "run_backtest":
                return self._run_backtest(
                    arguments["symbol"],
                    arguments["strategy"],
                    arguments["start_date"],
                    arguments.get("end_date")
                )
            elif function_name == "submit_paper_order":
                return self._submit_paper_order(arguments)
            elif function_name == "get_paper_portfolio":
                return self._get_paper_portfolio()
            elif function_name == "generate_strategy_from_description":
                return self._generate_strategy_from_description(
                    arguments["description"],
                    arguments.get("symbol", "AAPL")
                )
            elif function_name == "explain_strategy":
                return self._explain_strategy(
                    arguments["strategy_name"],
                    arguments.get("backtest_results")
                )
            elif function_name == "recommend_strategy_portfolio":
                return self._recommend_strategy_portfolio(
                    arguments["market_state"],
                    arguments["risk_tolerance"]
                )
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            logger.error(f"Error calling function {function_name}: {e}")
            return {"error": str(e)}
    
    def _get_market_data(self, symbol: str, start_date: str, end_date: Optional[str] = None):
        """获取市场数据"""
        from datetime import date
        from .data import DataConfig, download_ohlcv
        
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date) if end_date else None
        
        data_cfg = DataConfig(symbol=symbol, start=start, end=end)
        df = download_ohlcv(data_cfg)
        
        return {
            "symbol": symbol,
            "data_points": len(df),
            "date_range": f"{df.index[0]} to {df.index[-1]}",
            "summary": {
                "open": float(df["Open"].iloc[-1]),
                "high": float(df["High"].iloc[-1]),
                "low": float(df["Low"].iloc[-1]),
                "close": float(df["Close"].iloc[-1]),
                "volume": int(df["Volume"].iloc[-1])
            }
        }
    
    def _analyze_market_state(self, symbol: str, lookback_days: int = 60):
        """分析市场状态"""
        from datetime import date, timedelta
        from .data import DataConfig, download_ohlcv
        from .market_state import identify_market_state
        
        end = date.today()
        start = end - timedelta(days=lookback_days * 2)  # 获取更多数据用于计算
        
        data_cfg = DataConfig(symbol=symbol, start=start, end=end)
        df = download_ohlcv(data_cfg)
        
        market_state = identify_market_state(df)
        
        return {
            "symbol": symbol,
            "market_regime": market_state.regime.value,
            "volatility": market_state.volatility,
            "trend_strength": market_state.trend_strength,
            "is_bullish": market_state.is_bullish,
            "is_bearish": market_state.is_bearish,
            "adx": market_state.adx
        }
    
    def _get_strategy_recommendation(self, arguments: Dict[str, Any]):
        """获取策略推荐（打分 + 备选策略）。"""
        from .strategy_recommendation import recommend_strategy

        market_state = arguments.get("market_state")
        if not market_state:
            return {"error": "market_state is required"}

        symbol = arguments.get("symbol") or "UNKNOWN"
        result = recommend_strategy(
            symbol=symbol,
            market_state=market_state,
            volatility=arguments.get("volatility"),
            trend_strength=arguments.get("trend_strength"),
            is_bullish=arguments.get("is_bullish"),
            is_bearish=arguments.get("is_bearish"),
            risk_flags=arguments.get("risk_flags"),
        )
        if "error" in result:
            return result
        # 兼容 merge_observation / harness expected keys
        result["recommended_strategy"] = result.get("recommended_strategy")
        return result

    def _search_evidence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """检索证据库。"""
        from .evidence import EvidenceRetriever

        symbol = arguments.get("symbol")
        query = arguments.get("query")
        if not symbol or not query:
            return {"error": "symbol and query are required"}

        retriever = self.evidence_retriever or EvidenceRetriever.get_default()
        top_k = int(arguments.get("top_k") or 5)
        doc_types = arguments.get("doc_types")
        chunks = retriever.search(symbol, query, top_k=top_k, doc_types=doc_types)
        return {
            "symbol": symbol.upper(),
            "query": query,
            "count": len(chunks),
            "retrieved_documents": [c.to_dict() for c in chunks],
        }
    
    def _calculate_position_size(self, arguments: Dict[str, Any]):
        """计算仓位大小"""
        method = arguments["method"]
        
        if method == "kelly":
            from .position_sizing import kelly_position_size
            win_rate = arguments.get("win_rate", 0.5)
            avg_win = arguments.get("avg_win", 0.02)
            avg_loss = arguments.get("avg_loss", 0.01)
            position = kelly_position_size(win_rate, avg_win, avg_loss)
            return {
                "method": "kelly",
                "position_size": position,
                "parameters": {"win_rate": win_rate, "avg_win": avg_win, "avg_loss": avg_loss}
            }
        elif method == "risk_parity":
            from .position_sizing import risk_parity_position_size
            volatility = arguments.get("volatility", 0.2)
            position = risk_parity_position_size(volatility, target_volatility=0.15)
            return {
                "method": "risk_parity",
                "position_size": position,
                "parameters": {"volatility": volatility, "target_volatility": 0.15}
            }
        elif method == "volatility_targeting":
            # 简化实现
            volatility = arguments.get("volatility", 0.2)
            position = min(0.15 / volatility, 1.0)
            return {
                "method": "volatility_targeting",
                "position_size": position,
                "parameters": {"volatility": volatility, "target_volatility": 0.15}
            }
        return {"error": f"Unknown method: {method}"}
    
    def _run_backtest(self, symbol: str, strategy: str, start_date: str, end_date: Optional[str] = None):
        """运行回测"""
        from datetime import date
        from .agent import TradingAgent, AgentConfig, DataConfig, StrategyConfig, BacktestConfig
        
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date) if end_date else None
        
        agent_cfg = AgentConfig(
            data=DataConfig(symbol=symbol, start=start, end=end),
            strategy=StrategyConfig(name=strategy),
            backtest=BacktestConfig(initial_cash=100000)
        )
        
        agent = TradingAgent(agent_cfg)
        result = agent.run()
        
        stats = result.backtest_result.stats
        return {
            "symbol": symbol,
            "strategy": strategy,
            "total_return": stats["total_return"],
            "annual_return": stats["annual_return"],
            "sharpe": stats["sharpe"],
                "max_drawdown": stats["max_drawdown"]
            }
    
    def _generate_strategy_from_description(self, description: str, symbol: str = "AAPL"):
        """使用LLM从描述生成策略"""
        if not self.llm_strategy_generator:
            return {"error": "LLM strategy generator not available"}
        
        try:
            result = self.llm_strategy_generator.generate_strategy_from_description(
                description=description,
                symbol=symbol
            )
            return result
        except Exception as e:
            logger.error(f"Error generating strategy: {e}")
            return {"error": str(e)}
    
    def _explain_strategy(self, strategy_name: str, backtest_results: Optional[Dict] = None):
        """使用LLM解释策略"""
        if not self.llm_strategy_generator:
            return {"error": "LLM strategy generator not available"}
        
        try:
            from .llm_strategy import LLMStrategyExplainer
            # 获取API key
            api_key = getattr(self.llm_strategy_generator, 'api_key', None)
            explainer = LLMStrategyExplainer(api_key=api_key)
            
            explanation = explainer.explain_strategy_logic(strategy_name)
            
            if backtest_results:
                performance_analysis = explainer.analyze_strategy_performance(
                    strategy_name,
                    backtest_results
                )
                return {
                    "strategy_name": strategy_name,
                    "logic_explanation": explanation,
                    "performance_analysis": performance_analysis
                }
            
            return {
                "strategy_name": strategy_name,
                "explanation": explanation
            }
        except Exception as e:
            logger.error(f"Error explaining strategy: {e}")
            return {"error": str(e)}
    
    def _recommend_strategy_portfolio(self, market_state: str, risk_tolerance: str):
        """使用LLM推荐策略组合"""
        if not self.llm_strategy_generator:
            return {"error": "LLM strategy generator not available"}
        
        try:
            from .llm_strategy import LLMStrategyAdvisor
            # 获取API key
            api_key = getattr(self.llm_strategy_generator, 'api_key', None)
            advisor = LLMStrategyAdvisor(api_key=api_key)
            
            recommendation = advisor.recommend_strategy_portfolio(
                market_state=market_state,
                risk_tolerance=risk_tolerance
            )
            return recommendation
        except Exception as e:
            logger.error(f"Error recommending portfolio: {e}")
            return {"error": str(e)}

    def _submit_paper_order(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        from .execution.paper_trading import submit_paper_order

        return submit_paper_order(
            arguments["symbol"],
            arguments["side"],
            float(arguments["quantity"]),
            float(arguments["price"]),
        )

    def _get_paper_portfolio(self) -> Dict[str, Any]:
        from .execution.paper_trading import load_portfolio

        return load_portfolio()


__all__ = [
    "TradingFunctionCaller",
]

