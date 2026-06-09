"""
大模型Agent集成模块

实现LLM集成、Function Calling和RAG功能
"""

from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. LLM features will not work.")

try:
    try:
        from langchain_community.embeddings import OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        from langchain.embeddings import OpenAIEmbeddings
        from langchain.vectorstores import FAISS
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not installed. RAG features will not work.")


class TradingFunctionCaller:
    """交易相关的Function Calling工具"""
    
    def __init__(self, data_source=None, strategy_executor=None, llm_strategy_generator=None):
        self.data_source = data_source
        self.strategy_executor = strategy_executor
        self.llm_strategy_generator = llm_strategy_generator  # 新增：LLM策略生成器
    
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
                "description": "根据市场状态获取策略推荐",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "market_state": {
                            "type": "string",
                            "description": "市场状态：trending_up, trending_down, ranging, high_volatility, low_volatility",
                            "enum": ["trending_up", "trending_down", "ranging", "high_volatility", "low_volatility"]
                        }
                    },
                    "required": ["market_state"]
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
            }
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
                return self._get_strategy_recommendation(arguments["market_state"])
            elif function_name == "calculate_position_size":
                return self._calculate_position_size(arguments)
            elif function_name == "run_backtest":
                return self._run_backtest(
                    arguments["symbol"],
                    arguments["strategy"],
                    arguments["start_date"],
                    arguments.get("end_date")
                )
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
    
    def _get_strategy_recommendation(self, market_state: str):
        """获取策略推荐"""
        from .market_state import MarketRegime, get_optimal_strategy_for_regime
        
        regime_map = {
            "trending_up": MarketRegime.TRENDING_UP,
            "trending_down": MarketRegime.TRENDING_DOWN,
            "ranging": MarketRegime.RANGING,
            "high_volatility": MarketRegime.HIGH_VOLATILITY,
            "low_volatility": MarketRegime.LOW_VOLATILITY
        }
        
        regime = regime_map.get(market_state)
        if regime:
            from .market_state import MarketState
            mock_state = MarketState(
                regime=regime,
                volatility=0.2,
                trend_strength=0.5,
                adx=20.0,
                atr=2.0,
                bollinger_width=0.1,
                is_bullish=True,
                is_bearish=False
            )
            recommended = get_optimal_strategy_for_regime(mock_state)
            return {
                "market_state": market_state,
                "recommended_strategy": recommended,
                "reason": f"市场状态为{market_state}，适合使用{recommended}策略"
            }
        return {"error": f"Unknown market state: {market_state}"}
    
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


class RAGSystem:
    """RAG（检索增强生成）系统"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.vector_store = None
        self.embeddings = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """初始化嵌入模型"""
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, RAG features disabled")
            return
        
        try:
            if self.api_key:
                self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
            else:
                # 使用本地嵌入模型（如果有）
                logger.warning("No API key provided, using mock embeddings")
                self.embeddings = None
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self.embeddings = None
    
    def build_knowledge_base(self, trading_records: List[Dict[str, Any]]):
        """构建知识库"""
        if not LANGCHAIN_AVAILABLE or not self.embeddings:
            logger.warning("RAG not available, skipping knowledge base building")
            return
        
        try:
            # 将交易记录转换为文本
            texts = []
            for record in trading_records:
                text = f"""
交易记录：
股票代码: {record.get('symbol', 'N/A')}
策略: {record.get('strategy', 'N/A')}
日期: {record.get('date', 'N/A')}
收益率: {record.get('return', 0):.2%}
市场状态: {record.get('market_state', 'N/A')}
仓位: {record.get('position', 0):.2%}
结果: {record.get('result', 'N/A')}
                """.strip()
                texts.append(text)
            
            # 分割文本
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            documents = text_splitter.create_documents(texts)
            
            # 创建向量存储
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            logger.info(f"Built knowledge base with {len(documents)} documents")
        except Exception as e:
            logger.error(f"Failed to build knowledge base: {e}")
    
    def retrieve_relevant_experience(self, query: str, k: int = 3) -> List[str]:
        """检索相关历史经验"""
        if not self.vector_store:
            return []
        
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return [doc.page_content for doc in docs]
        except Exception as e:
            logger.error(f"Failed to retrieve: {e}")
            return []


class LLMTradingAgent:
    """集成大模型的交易Agent"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        enable_function_calling: bool = True,
        enable_rag: bool = True
    ):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package required. Install with: pip install openai")
        
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model
        
        # 初始化LLM策略生成器（用于原创功能）
        try:
            from .llm_strategy import LLMStrategyGenerator
            self.llm_strategy_generator = LLMStrategyGenerator(api_key=api_key, model=model)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM strategy generator: {e}")
            self.llm_strategy_generator = None
        
        self.function_caller = TradingFunctionCaller(llm_strategy_generator=self.llm_strategy_generator)
        self.rag_system = RAGSystem(api_key=api_key) if enable_rag else None
        self.enable_function_calling = enable_function_calling
        self.conversation_history = []
    
    def chat(self, user_message: str, use_functions: bool = True, use_rag: bool = True) -> str:
        """与LLM对话，支持Function Calling和RAG"""
        if not self.client:
            return "Error: OpenAI client not initialized. Please provide API key."
        
        # 构建消息
        messages = self.conversation_history + [{"role": "user", "content": user_message}]
        
        # 如果启用RAG，检索相关经验
        if use_rag and self.rag_system:
            relevant_experience = self.rag_system.retrieve_relevant_experience(user_message)
            if relevant_experience:
                rag_context = "\n\n相关历史经验：\n" + "\n".join(relevant_experience)
                messages[-1]["content"] = user_message + rag_context
        
        # 准备Function Calling
        functions = None
        if use_functions and self.enable_function_calling:
            functions = self.function_caller.get_available_functions()
        
        try:
            # 调用LLM
            if functions:
                # OpenAI新的API使用tools参数
                try:
                    # 尝试使用新API（tools）
                    tools = [{"type": "function", "function": f} for f in functions]
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto"
                    )
                except Exception:
                    # 回退到旧API（functions）
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        functions=functions,
                        function_call="auto"
                    )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
            
            message = response.choices[0].message
            
            # 处理Function Calling（兼容新旧API）
            function_call = None
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # 新API格式
                function_call = message.tool_calls[0].function
            elif hasattr(message, 'function_call') and message.function_call:
                # 旧API格式
                function_call = message.function_call
            
            if function_call:
                function_name = function_call.name if hasattr(function_call, 'name') else function_call.get('name')
                import json
                if hasattr(function_call, 'arguments'):
                    arguments = json.loads(function_call.arguments)
                else:
                    arguments = json.loads(function_call.get('arguments', '{}'))
                
                # 执行函数
                function_result = self.function_caller.call_function(function_name, arguments)
                
                # 将结果返回给LLM（兼容新旧API）
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # 新API格式
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": message.tool_calls
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": message.tool_calls[0].id,
                        "name": function_name,
                        "content": json.dumps(function_result)
                    })
                else:
                    # 旧API格式
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "name": function_name,
                            "arguments": json.dumps(arguments)
                        }
                    })
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(function_result)
                    })
                
                # 再次调用LLM生成最终回复
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                result = final_response.choices[0].message.content
            else:
                result = message.content
            
            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM chat: {e}")
            return f"Error: {str(e)}"
    
    def analyze_market_with_llm(self, symbol: str, query: Optional[str] = None) -> str:
        """使用LLM分析市场"""
        if not query:
            query = f"请分析{symbol}的市场情况，并给出交易建议"
        
        prompt = f"""
作为量化交易专家，请分析以下股票：
股票代码: {symbol}

请提供：
1. 市场趋势分析
2. 适合的交易策略建议
3. 风险提示

如果需要获取实际数据，可以使用可用的工具函数。
        """
        
        return self.chat(prompt, use_functions=True, use_rag=True)
    
    def generate_strategy_explanation(self, strategy_name: str, results: Dict[str, Any]) -> str:
        """使用LLM生成策略解释"""
        prompt = f"""
请解释以下交易策略的回测结果：

策略名称: {strategy_name}
总收益率: {results.get('total_return', 0):.2%}
年化收益率: {results.get('annual_return', 0):.2%}
夏普比率: {results.get('sharpe', 0):.4f}
最大回撤: {results.get('max_drawdown', 0):.2%}

请提供：
1. 策略表现评价
2. 风险分析
3. 改进建议
        """
        
        return self.chat(prompt, use_functions=False, use_rag=True)
    
    def build_knowledge_base_from_results(self, results: List[Dict[str, Any]]):
        """从回测结果构建知识库"""
        if self.rag_system:
            self.rag_system.build_knowledge_base(results)


__all__ = [
    "TradingFunctionCaller",
    "RAGSystem",
    "LLMTradingAgent",
]

