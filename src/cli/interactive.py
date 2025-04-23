from datetime import date, timedelta
import questionary
from questionary import Choice, Style

from src.config.config import Config, SimulationConfig, Period, StrategyItem, BrokerItem, DataProviderItem
from src.config.strategy_config import STRATEGY_CONFIG
from src.config.broker_config import BROKER_CONFIG
from src.config.data_provider_config import DATA_PROVIDER_CONFIG

# Define a consistent questionary style
CLI_STYLE = Style([
    ('selected', 'fg:green bold'),
    ('pointer', 'fg:green bold'),
    ('highlighted', 'fg:green'),
    ('answer', 'fg:green bold'),
])

def interactive_start():
    """Prompt the user to configure a single strategy interactively using multi-choice menus."""
    # Operation selection
    operation = questionary.select(
        "Choose operation:",
        choices=[Choice('Backtest','backtest'), Choice('Live Trading','live')],
        style=CLI_STYLE
    ).ask()
    if not operation:
        return None

    # Broker selection & config (live only)
    broker_config = {}
    paper = False
    shadow_mode = False
    if operation == 'live':
        broker_choice = questionary.select(
            "Choose a broker:",
            choices=[Choice(meta['display_name'], value=name) for name, meta in BROKER_CONFIG.items()],
            style=CLI_STYLE
        ).ask()
        if not broker_choice:
            return None
        paper = questionary.confirm("Route orders to paper trading?").ask()
        shadow_mode = questionary.confirm("Enable shadow mode (signals only)?").ask()
        if broker_choice == 'shadow':
            webhook = questionary.text(
                "Discord Webhook URL for shadow broker (leave blank to disable):",
                style=CLI_STYLE
            ).ask() or ""
            if webhook:
                broker_config["discord_webhook_url"] = webhook
    else:
        broker_choice = next(iter(BROKER_CONFIG))  # placeholder for backtest

    # Data provider selection
    data_provider_choice = questionary.select(
        "Choose a data provider:",
        choices=[Choice(meta['display_name'], value=name) for name, meta in DATA_PROVIDER_CONFIG.items()],
        style=CLI_STYLE
    ).ask()
    if not data_provider_choice:
        return None

    # Timeframe selection based on operation
    provider_meta = DATA_PROVIDER_CONFIG[data_provider_choice]
    provider_cls = provider_meta['provider_class']
    if operation == 'live':
        timeframe_choices = getattr(provider_cls, 'supported_live_timeframes', [])
    else:
        timeframe_choices = getattr(provider_cls, 'supported_historical_timeframes', [])
    timeframe = questionary.select(
        "Select timeframe:",
        choices=[Choice(tf, value=tf) for tf in timeframe_choices],
        style=CLI_STYLE
    ).ask() or SimulationConfig().timeframe

    # Backtest config
    if operation == 'backtest':
        start_cash_str = questionary.text("Start cash:", default=str(100000), style=CLI_STYLE).ask() or str(100000)
        start_cash = float(start_cash_str)
        slippage_str = questionary.text("Slippage:", default=str(0.0001), style=CLI_STYLE).ask() or str(0.0001)
        slippage = float(slippage_str)
        commission_str = questionary.text("Commission:", default=str(0.0002), style=CLI_STYLE).ask() or str(0.0002)
        commission = float(commission_str)
        default_end = date.today().isoformat()
        default_start = (date.today() - timedelta(days=180)).isoformat()
        start_str = questionary.text("Start date (YYYY-MM-DD):", default=default_start, style=CLI_STYLE).ask() or default_start
        end_str = questionary.text("End date (YYYY-MM-DD):", default=default_end, style=CLI_STYLE).ask() or default_end
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)

        sim = SimulationConfig(timeframe=timeframe, start_cash=start_cash, slippage=slippage, commission=commission, period=Period(start=start_date, end=end_date))
    else:
        # Create default simulation config for live trading
        start_str = date.today().isoformat()
        end_str = date.today().isoformat()
        sim = SimulationConfig()

    # Strategy selection
    choice = questionary.select(
        "Choose a strategy to run:",
        choices=[Choice(meta['display_name'], value=name) for name, meta in STRATEGY_CONFIG.items()],
        style=CLI_STYLE
    ).ask()
    if not choice:
        return None
    
    # Symbol and additional strategy parameters
    symbol = questionary.text("Symbol:", default="SPY", style=CLI_STYLE).ask() or "SPY"
    config_model = STRATEGY_CONFIG[choice].get('config_model')
    params = {}
    if config_model:
        params['symbol'] = symbol
        params['timeframe'] = timeframe
        params['period'] = {'start': start_str, 'end': end_str}
        for field_name, field_info in config_model.model_fields.items():
            if field_name in ('symbol', 'timeframe', 'period'):
                continue
            default_val = field_info.get_default() or ''
            answer = questionary.text(f"{field_name.replace('_',' ').title()} [{default_val}]:", default=str(default_val), style=CLI_STYLE).ask()
            if field_info.annotation == int:
                params[field_name] = int(answer)
            elif field_info.annotation == float:
                params[field_name] = float(answer)
            else:
                params[field_name] = answer

    return Config(
        simulation=sim,
        broker=BrokerItem(name=broker_choice, config=broker_config),
        data_provider=DataProviderItem(name=data_provider_choice, config={}),
        strategies=[
            StrategyItem(
                name=choice,
                enabled=True,
                operation=operation,
                paper=paper,
                shadow_mode=shadow_mode,
                config=params
            )
        ]
    ) 