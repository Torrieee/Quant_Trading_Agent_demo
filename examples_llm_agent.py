"""
LLM Agent集成示例

展示如何使用Function Calling和RAG功能
"""

import os
from datetime import date, timedelta

from quant_agent.llm_agent import LLMTradingAgent, TradingFunctionCaller, RAGSystem


def example_function_calling():
    """示例1：Function Calling功能"""
    print("=" * 70)
    print("示例1：Function Calling功能")
    print("=" * 70)
    
    # 创建Function Caller（不需要API key）
    function_caller = TradingFunctionCaller()
    
    # 查看可用函数
    print("\n可用函数列表：")
    functions = function_caller.get_available_functions()
    for func in functions:
        print(f"  - {func['name']}: {func['description']}")
    
    # 测试调用函数
    print("\n测试：获取市场数据")
    result = function_caller.call_function(
        "get_market_data",
        {
            "symbol": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01"
        }
    )
    print(f"结果: {result}")
    
    print("\n测试：分析市场状态")
    result = function_caller.call_function(
        "analyze_market_state",
        {
            "symbol": "AAPL",
            "lookback_days": 60
        }
    )
    print(f"结果: {result}")
    
    print("\n测试：获取策略推荐")
    result = function_caller.call_function(
        "get_strategy_recommendation",
        {
            "market_state": "trending_up"
        }
    )
    print(f"结果: {result}")
    
    print("\n测试：计算仓位大小")
    result = function_caller.call_function(
        "calculate_position_size",
        {
            "method": "kelly",
            "win_rate": 0.6,
            "avg_win": 0.03,
            "avg_loss": 0.02
        }
    )
    print(f"结果: {result}")


def example_llm_agent_with_function_calling():
    """示例2：使用LLM Agent进行对话（需要OpenAI API key）"""
    print("\n" + "=" * 70)
    print("示例2：LLM Agent对话（Function Calling）")
    print("=" * 70)
    
    # 检查API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY环境变量")
        print("   设置方法：")
        print("   Windows: set OPENAI_API_KEY=your_key")
        print("   Linux/Mac: export OPENAI_API_KEY=your_key")
        print("\n   跳过LLM示例，仅展示Function Calling功能")
        return
    
    try:
        # 创建LLM Agent
        agent = LLMTradingAgent(
            api_key=api_key,
            model="gpt-3.5-turbo",
            enable_function_calling=True,
            enable_rag=False  # 先不使用RAG
        )
        
        print("\n与LLM Agent对话（支持Function Calling）：")
        print("-" * 70)
        
        # 示例对话
        queries = [
            "请帮我获取AAPL从2023-01-01到2024-01-01的市场数据",
            "分析一下AAPL的市场状态",
            "根据当前市场状态，推荐一个交易策略",
            "如果我的胜率是60%，平均盈利3%，平均亏损2%，应该用多少仓位？"
        ]
        
        for query in queries:
            print(f"\n用户: {query}")
            response = agent.chat(query, use_functions=True, use_rag=False)
            print(f"Agent: {response}")
            print("-" * 70)
    
    except Exception as e:
        print(f"\n错误: {e}")
        print("请检查API key是否正确，或网络连接是否正常")


def example_rag_system():
    """示例3：RAG系统（需要OpenAI API key）"""
    print("\n" + "=" * 70)
    print("示例3：RAG（检索增强生成）系统")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY，跳过RAG示例")
        return
    
    try:
        # 创建RAG系统
        rag = RAGSystem(api_key=api_key)
        
        # 模拟历史交易记录
        trading_records = [
            {
                "symbol": "AAPL",
                "strategy": "mean_reversion",
                "date": "2023-01-15",
                "return": 0.025,
                "market_state": "ranging",
                "position": 0.5,
                "result": "盈利"
            },
            {
                "symbol": "MSFT",
                "strategy": "momentum",
                "date": "2023-02-20",
                "return": 0.035,
                "market_state": "trending_up",
                "position": 0.8,
                "result": "盈利"
            },
            {
                "symbol": "TSLA",
                "strategy": "mean_reversion",
                "date": "2023-03-10",
                "return": -0.015,
                "market_state": "high_volatility",
                "position": 0.6,
                "result": "亏损"
            }
        ]
        
        print("\n构建知识库...")
        rag.build_knowledge_base(trading_records)
        print("✓ 知识库构建完成")
        
        # 检索相关经验
        print("\n检索相关经验：")
        queries = [
            "在震荡市场中，均值回归策略的表现如何？",
            "高波动率市场应该用什么策略？",
            "AAPL的交易经验"
        ]
        
        for query in queries:
            print(f"\n查询: {query}")
            results = rag.retrieve_relevant_experience(query, k=2)
            for i, result in enumerate(results, 1):
                print(f"  结果{i}: {result[:100]}...")
    
    except Exception as e:
        print(f"\n错误: {e}")
        print("请确保已安装langchain和faiss-cpu")


def example_integrated_llm_agent():
    """示例4：集成Function Calling和RAG的完整Agent"""
    print("\n" + "=" * 70)
    print("示例4：集成Function Calling和RAG的完整Agent")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY，跳过完整示例")
        return
    
    try:
        # 创建完整的LLM Agent
        agent = LLMTradingAgent(
            api_key=api_key,
            model="gpt-3.5-turbo",
            enable_function_calling=True,
            enable_rag=True
        )
        
        # 构建知识库
        trading_records = [
            {
                "symbol": "AAPL",
                "strategy": "mean_reversion",
                "date": "2023-01-15",
                "return": 0.025,
                "market_state": "ranging",
                "position": 0.5,
                "result": "盈利"
            }
        ]
        agent.build_knowledge_base_from_results(trading_records)
        
        # 使用Agent分析市场
        print("\n使用LLM Agent分析市场（集成Function Calling和RAG）：")
        print("-" * 70)
        
        response = agent.analyze_market_with_llm("AAPL")
        print(f"Agent分析结果:\n{response}")
        
    except Exception as e:
        print(f"\n错误: {e}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print(" " * 20 + "LLM Agent集成示例")
    print("=" * 70)
    print("\n本示例将展示：")
    print("1. Function Calling功能")
    print("2. LLM Agent对话（需要OpenAI API key）")
    print("3. RAG系统（需要OpenAI API key）")
    print("4. 完整集成示例")
    print("=" * 70)
    
    try:
        # 示例1：Function Calling（不需要API key）
        example_function_calling()
        
        # 示例2：LLM Agent（需要API key）
        example_llm_agent_with_function_calling()
        
        # 示例3：RAG系统（需要API key）
        example_rag_system()
        
        # 示例4：完整集成（需要API key）
        example_integrated_llm_agent()
        
        print("\n" + "=" * 70)
        print("所有示例完成！")
        print("=" * 70)
        print("\n💡 提示：")
        print("- Function Calling功能不需要API key，可以直接使用")
        print("- LLM和RAG功能需要设置OPENAI_API_KEY环境变量")
        print("- 这些功能可以显著提升项目与大模型Agent岗位的匹配度")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()




