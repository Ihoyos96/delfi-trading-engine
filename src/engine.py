from src.config.config import Config
from src.config.strategy_config import STRATEGY_CONFIG  # adjust path if needed
from src.config.broker_config import BROKER_CONFIG
from src.config.data_provider_config import DATA_PROVIDER_CONFIG
from src.brokers.shadow_broker import ShadowBroker
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo


def run_from_config(cfg: Config) -> None:
    """Execute all enabled strategies defined in the Config model."""
    # Warn if running outside US market hours (9:30 to 16:00 ET Mon-Fri)
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5 or now_et.time() < dt_time(9, 30) or now_et.time() >= dt_time(16, 0):
        print("\033[93mWARNING: Market is closed, you may not receive updates until market opens.\033[0m")

    # Unpack global simulation parameters (cash, slippage, commission)
    sim = cfg.simulation
    start_cash = sim.start_cash
    slippage = sim.slippage
    commission = sim.commission

    # Instantiate data provider from config (provider handles its own env setup)
    dp_name = cfg.data_provider.name
    if dp_name not in DATA_PROVIDER_CONFIG:
        raise ValueError(f"Unknown data provider '{dp_name}'")
    provider_meta = DATA_PROVIDER_CONFIG[dp_name]
    provider_cls = provider_meta["provider_class"]
    data_provider = provider_cls(**cfg.data_provider.config)

    # Execute each strategy
    for strat_item in cfg.strategies:
        name = strat_item.name
        # Skip disabled strategies
        if not strat_item.enabled:
            print(f"Skipping disabled strategy '{name}'")
            continue
        if name not in STRATEGY_CONFIG:
            print(f"Unknown strategy '{name}'")
            continue
        meta = STRATEGY_CONFIG[name]
        StrategyClass = meta["strategy_class"]
        params_model = meta.get("config_model")
        # Parse and validate parameters
        try:
            if params_model:
                params = params_model.parse_obj(strat_item.config)
            else:
                params = strat_item.config
        except Exception as e:
            print(f"Invalid parameters for '{name}': {e}")
            continue

        print(f"=== Running strategy '{name}' ({meta['display_name']}) | operation={strat_item.operation} shadow_mode={strat_item.shadow_mode} ===")
        # Dispatch based on operation
        if strat_item.operation == "backtest":
            # Backtest mode: run via Backtester, using the configured data provider
            from src.backtester.backtester import Backtester
            print(f"Running backtest for '{name}'...")
            bt = Backtester(
                StrategyClass,
                params,
                data_provider,
                start_cash=sim.start_cash,
                slippage=sim.slippage,
                commission=sim.commission
            )
            metrics = bt.run(
                params.symbol,
                params.period.start,
                params.period.end,
                params.timeframe
            )
            print(f"{name} backtest metrics: {metrics}\n")

        elif strat_item.shadow_mode:
            print(f"Running '{name}' in shadow mode (only signal notifications)")
            broker = ShadowBroker(paper=strat_item.paper, **cfg.broker.config)    
            instance = StrategyClass(params, broker, data_provider)
            instance.run()

        else:
            # Live trading: instantiate broker & run using configured broker and data provider
            # Determine broker class from registry
            print(f"Running '{name}' in live mode")

            broker_name = cfg.broker.name
            if broker_name not in BROKER_CONFIG:
                raise ValueError(f"Unknown broker '{broker_name}'")
            broker_meta = BROKER_CONFIG[broker_name]
            broker_cls = broker_meta["broker_class"]
            # Broker handles its own credential setup; pass paper flag and any extra config
            broker = broker_cls(paper=strat_item.paper, **cfg.broker.config)

            # Instantiate strategy with broker and data provider then run
            instance = StrategyClass(params, broker, data_provider)
            instance.run() 