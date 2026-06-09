"""
强化学习训练示例

展示如何使用强化学习训练交易Agent
"""

import datetime as dt

from quant_agent import DataConfig
from quant_agent.rl_trainer import train_rl_agent, evaluate_rl_agent, create_trading_env


def example_train_rl_agent():
    """示例1：训练RL Agent"""
    print("=" * 60)
    print("示例1：训练强化学习Agent")
    print("=" * 60)
    
    # 配置训练数据
    train_data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2018, 1, 1),
        end=dt.date(2022, 1, 1),  # 训练集
    )
    
    # 配置验证数据
    eval_data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2022, 1, 1),
        end=dt.date(2023, 1, 1),  # 验证集
    )
    
    print(f"\n训练数据: {train_data_cfg.symbol} ({train_data_cfg.start} to {train_data_cfg.end})")
    print(f"验证数据: {eval_data_cfg.symbol} ({eval_data_cfg.start} to {eval_data_cfg.end})")
    
    # 训练模型
    print("\n开始训练PPO Agent...")
    print("注意：训练可能需要较长时间，请耐心等待...")
    
    try:
        model, training_info = train_rl_agent(
            data_cfg=train_data_cfg,
            algorithm="PPO",  # 可以使用 'PPO', 'A2C', 'DQN', 'SAC', 'TD3'
            total_timesteps=50000,  # 训练步数（可以根据需要调整）
            initial_cash=100000.0,
            fee_rate=0.0005,
            max_position=1.0,
            reward_type="sharpe",  # 奖励类型：'return', 'sharpe', 'risk_adjusted'
            model_save_path="models/rl_agent_ppo.zip",
            eval_data_cfg=eval_data_cfg,
            verbose=1,
        )
        
        print("\n训练完成！")
        print(f"模型已保存到: {training_info['model_path']}")
        
        return model, training_info
        
    except ImportError as e:
        print(f"\n错误: {e}")
        print("\n请先安装stable-baselines3:")
        print("  pip install stable-baselines3[extra]")
        return None, None


def example_evaluate_rl_agent():
    """示例2：评估训练好的RL Agent"""
    print("\n" + "=" * 60)
    print("示例2：评估RL Agent")
    print("=" * 60)
    
    try:
        from stable_baselines3 import PPO
        
        # 加载模型
        model_path = "models/rl_agent_ppo.zip"
        print(f"\n加载模型: {model_path}")
        
        try:
            model = PPO.load(model_path)
        except FileNotFoundError:
            print(f"模型文件不存在: {model_path}")
            print("请先运行训练示例生成模型")
            return
        
        # 配置测试数据
        test_data_cfg = DataConfig(
            symbol="AAPL",
            start=dt.date(2023, 1, 1),
            end=dt.date(2024, 1, 1),  # 测试集
        )
        
        print(f"\n测试数据: {test_data_cfg.symbol} ({test_data_cfg.start} to {test_data_cfg.end})")
        
        # 评估模型
        print("\n评估Agent表现...")
        results = evaluate_rl_agent(
            model=model,
            data_cfg=test_data_cfg,
            initial_cash=100000.0,
            fee_rate=0.0005,
            max_position=1.0,
            num_episodes=5,  # 运行5次取平均
        )
        
        print("\n评估结果:")
        print("-" * 60)
        print(f"平均收益率: {results['mean_return']:.2%}")
        print(f"收益率标准差: {results['std_return']:.2%}")
        print(f"评估回合数: {results['num_episodes']}")
        print(f"各回合收益: {[f'{r:.2%}' for r in results['episode_returns']]}")
        print("-" * 60)
        
    except ImportError:
        print("\n请先安装stable-baselines3:")
        print("  pip install stable-baselines3[extra]")


def example_compare_algorithms():
    """示例3：对比不同RL算法"""
    print("\n" + "=" * 60)
    print("示例3：对比不同RL算法")
    print("=" * 60)
    
    train_data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2020, 1, 1),
        end=dt.date(2022, 1, 1),
    )
    
    test_data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2022, 1, 1),
        end=dt.date(2023, 1, 1),
    )
    
    algorithms = ["PPO", "A2C"]  # 可以添加更多算法
    
    results = {}
    
    for algo in algorithms:
        print(f"\n训练 {algo}...")
        try:
            model, _ = train_rl_agent(
                data_cfg=train_data_cfg,
                algorithm=algo,
                total_timesteps=20000,  # 较少的步数用于快速对比
                model_save_path=f"models/rl_agent_{algo.lower()}.zip",
            )
            
            # 评估
            eval_results = evaluate_rl_agent(
                model=model,
                data_cfg=test_data_cfg,
                num_episodes=3,
            )
            
            results[algo] = eval_results["mean_return"]
            print(f"{algo} 平均收益: {eval_results['mean_return']:.2%}")
            
        except Exception as e:
            print(f"{algo} 训练失败: {e}")
            results[algo] = None
    
    # 对比结果
    print("\n算法对比:")
    print("-" * 60)
    for algo, return_val in results.items():
        if return_val is not None:
            print(f"{algo:>10}: {return_val:>10.2%}")
    print("-" * 60)


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("强化学习训练示例")
    print("=" * 60)
    print("\n本示例将展示以下功能：")
    print("1. 训练RL Agent（PPO算法）")
    print("2. 评估训练好的Agent")
    print("3. 对比不同RL算法")
    print("=" * 60)
    print("\n⚠️  注意：")
    print("- 训练需要安装 stable-baselines3: pip install stable-baselines3[extra]")
    print("- 训练可能需要较长时间，建议先用较少的timesteps测试")
    print("- 模型会保存到 models/ 目录")
    print("=" * 60)
    
    try:
        # 示例1：训练
        model, training_info = example_train_rl_agent()
        
        if model is not None:
            # 示例2：评估
            example_evaluate_rl_agent()
            
            # 示例3：对比（可选，比较耗时）
            print("\n是否运行算法对比？（需要较长时间，输入 y/n）")
            choice = input().strip().lower()
            if choice == 'y':
                example_compare_algorithms()
        
        print("\n" + "=" * 60)
        print("所有示例完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

