"""
LLM原创功能示例

展示真正利用LLM能力的原创功能：
1. 自然语言策略生成
2. 策略解释和分析
3. 智能策略组合推荐
"""

import os
from datetime import date

from quant_agent.llm_strategy import (
    LLMStrategyAdvisor,
    LLMStrategyExplainer,
    LLMStrategyGenerator,
)


def example_generate_strategy_from_description():
    """示例1：从自然语言描述生成策略"""
    print("=" * 70)
    print("示例1：自然语言策略生成（LLM原创功能）")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY，跳过此示例")
        print("   设置方法：")
        print("   Windows: set OPENAI_API_KEY=your_key")
        print("   Linux/Mac: export OPENAI_API_KEY=your_key")
        return
    
    try:
        generator = LLMStrategyGenerator(api_key=api_key)
        
        # 示例：用自然语言描述策略
        descriptions = [
            "当价格低于20日均线时买入，高于时卖出",
            "当RSI低于30时买入，高于70时卖出",
            "当短期均线上穿长期均线时买入，下穿时卖出"
        ]
        
        for desc in descriptions:
            print(f"\n策略描述: {desc}")
            print("-" * 70)
            
            result = generator.generate_strategy_from_description(
                description=desc,
                symbol="AAPL"
            )
            
            if "error" not in result:
                print(f"策略名称: {result.get('strategy_name', 'N/A')}")
                print(f"策略逻辑: {result.get('logic', 'N/A')}")
                print(f"适用市场: {result.get('suitable_market', 'N/A')}")
                print(f"风险提示: {result.get('risk_warning', 'N/A')}")
            else:
                print(f"错误: {result.get('error')}")
    
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def example_explain_strategy():
    """示例2：使用LLM解释策略"""
    print("\n" + "=" * 70)
    print("示例2：策略解释和分析（LLM原创功能）")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY，跳过此示例")
        return
    
    try:
        explainer = LLMStrategyExplainer(api_key=api_key)
        
        # 解释策略逻辑
        print("\n解释均值回归策略的逻辑：")
        print("-" * 70)
        explanation = explainer.explain_strategy_logic(
            strategy_name="均值回归策略",
            strategy_config={"mr_window": 20, "mr_threshold": 1.0}
        )
        print(explanation)
        
        # 分析策略表现
        print("\n\n分析策略回测表现：")
        print("-" * 70)
        backtest_results = {
            "total_return": 0.15,
            "annual_return": 0.12,
            "sharpe": 1.5,
            "max_drawdown": -0.08,
            "annual_volatility": 0.15
        }
        
        analysis = explainer.analyze_strategy_performance(
            strategy_name="均值回归策略",
            backtest_results=backtest_results
        )
        print(analysis)
    
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def example_recommend_strategy_portfolio():
    """示例3：推荐策略组合"""
    print("\n" + "=" * 70)
    print("示例3：智能策略组合推荐（LLM原创功能）")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY，跳过此示例")
        return
    
    try:
        advisor = LLMStrategyAdvisor(api_key=api_key)
        
        # 不同市场状态和风险偏好的组合
        scenarios = [
            {"market_state": "trending_up", "risk_tolerance": "high"},
            {"market_state": "ranging", "risk_tolerance": "medium"},
            {"market_state": "high_volatility", "risk_tolerance": "low"}
        ]
        
        for scenario in scenarios:
            print(f"\n市场状态: {scenario['market_state']}, 风险偏好: {scenario['risk_tolerance']}")
            print("-" * 70)
            
            recommendation = advisor.recommend_strategy_portfolio(
                market_state=scenario["market_state"],
                risk_tolerance=scenario["risk_tolerance"],
                available_strategies=["mean_reversion", "momentum"]
            )
            
            if "error" not in recommendation:
                print("推荐策略组合:")
                for strategy in recommendation.get("recommended_strategies", []):
                    print(f"  - {strategy.get('name')}: 权重 {strategy.get('weight', 0):.1%}, 理由: {strategy.get('reason', 'N/A')}")
                print(f"\n预期收益率: {recommendation.get('expected_return', 0):.2%}")
                print(f"预期风险: {recommendation.get('expected_risk', 0):.2%}")
                print(f"风险提示: {recommendation.get('risk_warning', 'N/A')}")
            else:
                print(f"错误: {recommendation.get('error')}")
    
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def example_strategy_improvement():
    """示例4：策略改进建议"""
    print("\n" + "=" * 70)
    print("示例4：策略改进建议（LLM原创功能）")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  未设置OPENAI_API_KEY，跳过此示例")
        return
    
    try:
        advisor = LLMStrategyAdvisor(api_key=api_key)
        
        # 当前策略表现
        current_performance = {
            "annual_return": 0.08,
            "sharpe": 0.8,
            "max_drawdown": -0.15
        }
        
        market_conditions = {
            "volatility": "high",
            "trend": "weak"
        }
        
        print("\n当前策略表现:")
        print(f"  年化收益率: {current_performance['annual_return']:.2%}")
        print(f"  夏普比率: {current_performance['sharpe']:.4f}")
        print(f"  最大回撤: {current_performance['max_drawdown']:.2%}")
        
        print("\nLLM改进建议:")
        print("-" * 70)
        
        suggestions = advisor.suggest_strategy_improvement(
            strategy_name="均值回归策略",
            current_performance=current_performance,
            market_conditions=market_conditions
        )
        
        print(suggestions)
    
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print(" " * 15 + "LLM原创功能示例")
    print("=" * 70)
    print("\n本示例展示真正利用LLM能力的原创功能：")
    print("1. 自然语言策略生成 - LLM从描述生成策略")
    print("2. 策略解释和分析 - LLM解释策略逻辑和表现")
    print("3. 智能策略组合推荐 - LLM推荐策略组合")
    print("4. 策略改进建议 - LLM提供优化建议")
    print("=" * 70)
    print("\n⚠️  注意：这些功能需要OpenAI API key")
    print("   设置方法：")
    print("   Windows: set OPENAI_API_KEY=your_key")
    print("   Linux/Mac: export OPENAI_API_KEY=your_key")
    print("=" * 70)
    
    try:
        example_generate_strategy_from_description()
        example_explain_strategy()
        example_recommend_strategy_portfolio()
        example_strategy_improvement()
        
        print("\n" + "=" * 70)
        print("所有示例完成！")
        print("=" * 70)
        print("\n💡 这些功能真正利用了LLM的能力：")
        print("   - 自然语言理解和生成")
        print("   - 策略分析和解释")
        print("   - 智能推荐和优化建议")
        print("   不是简单的功能包装，而是LLM的独特能力！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()




