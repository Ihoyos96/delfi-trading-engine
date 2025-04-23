use std::env;
use tokio::{sync::mpsc, time::{interval, Duration}};
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};
use futures_util::{StreamExt, SinkExt};
use serde::{Deserialize, Serialize};
use serde_json::json;
use redis::AsyncCommands;
use chrono::Utc;
use clap::Parser;

#[derive(Debug, Deserialize)]
struct AlpacaStreamMsg {
    stream: String,
    data: serde_json::Value,
}

#[derive(Debug)]
struct TradeEvent {
    price: f64,
    size: f64,
}

#[derive(Serialize)]
struct Bar {
    symbol: String,
    timestamp: String,
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    volume: f64,
}

/// Bar Aggregator: subscribes to Alpaca trades and publishes 1s bars to Redis
#[derive(Parser)]
#[command(name = "bar_aggregator")]
struct Args {
    /// Ticker symbol to subscribe to (e.g. SPY)
    #[arg(long)]
    symbol: String,
}

// Allow configuring which Alpaca stream to use (SIP or IEX). Default to IEX for free data.
const DEFAULT_WEBSOCKET_URL: &str = "wss://stream.data.alpaca.markets/v2/iex";

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Parse command-line arguments
    let args = Args::parse();
    let symbol = args.symbol;
    // Load Alpaca API credentials from env
    let api_key = env::var("APCA_API_KEY_ID")?;
    let api_secret = env::var("APCA_API_SECRET_KEY")?;
    let websocket_url = std::env::var("ALPACA_WS_URL").unwrap_or_else(|_| DEFAULT_WEBSOCKET_URL.to_string());
    if websocket_url.contains("/v2/sip") {
        eprintln!("[Agg][Warning] Using SIP feed; ensure your account has SIP subscription");
    } else {
        println!("[Agg] Using IEX feed at {}", websocket_url);
    }
    println!("[Agg] Connecting to {}", websocket_url);
    let (ws_stream, _) = connect_async(websocket_url).await?;
    println!("[Agg] WebSocket connection established");
    let (mut write, mut read) = ws_stream.split();

    // Authenticate
    println!("[Agg] Sending auth message");
    let auth_msg = json!({"action":"auth","key":api_key,"secret":api_secret});
    write.send(Message::Text(auth_msg.to_string())).await?;
    println!("[Agg] Auth message sent");

    // Subscribe to trade and quote streams for the provided symbol
    println!("[Agg] Subscribing to trades and quotes for symbol: {}", symbol);
    let sub_msg = json!({"action":"subscribe","trades":[symbol.clone()],"quotes":[symbol.clone()]});
    write.send(Message::Text(sub_msg.to_string())).await?;
    println!("[Agg] Subscribe message sent: {}", sub_msg);

    // Setup Redis connection
    let redis_url = env::var("REDIS_URL").unwrap_or_else(|_| "redis://127.0.0.1/".into());
    let client = redis::Client::open(redis_url)?;
    let mut redis_conn = client.get_async_connection().await?;

    // Channel for raw trade events
    let (tx, mut rx) = mpsc::unbounded_channel::<TradeEvent>();

    // Task: read websocket messages and push trades to channel
    let symbol_clone = symbol.clone();
    tokio::spawn(async move {
        println!("[Agg] Entered WebSocket read loop");
        while let Some(msg) = read.next().await {
            println!("[Agg] Raw WS msg: {:?}", msg);
            if let Ok(Message::Text(txt)) = msg {
                println!("[Agg] WS text payload: {}", txt);
                if let Ok(parsed) = serde_json::from_str::<AlpacaStreamMsg>(&txt) {
                    println!("[Agg] Parsed stream msg: {}", parsed.stream);
                    let trade_prefix = format!("T.{}", symbol_clone);
                    let quote_prefix = format!("Q.{}", symbol_clone);
                    if parsed.stream == trade_prefix {
                        if let Some(arr) = parsed.data.as_array() {
                            for item in arr {
                                println!("[Agg] Processing trade item: {:?}", item);
                                let price = item["p"].as_f64().unwrap_or(0.0);
                                let size = item["s"].as_f64().unwrap_or(0.0);
                                println!("[Agg] Sending TradeEvent: price={}, size={}", price, size);
                                let _ = tx.send(TradeEvent { price, size });
                            }
                        }
                    } else if parsed.stream == quote_prefix {
                        if let Some(arr) = parsed.data.as_array() {
                            for item in arr {
                                println!("[Agg] Processing quote item: {:?}", item);
                                // use mid-price as tick
                                let bid = item["bp"].as_f64().unwrap_or(0.0);
                                let ask = item["ap"].as_f64().unwrap_or(0.0);
                                let price = (bid + ask) / 2.0;
                                let size = item["bs"].as_f64().unwrap_or(0.0) + item["as"].as_f64().unwrap_or(0.0);
                                println!("[Agg] Sending QuoteEvent as TradeEvent: price={}, size={}", price, size);
                                let _ = tx.send(TradeEvent { price, size });
                            }
                        }
                    }
                }
            }
        }
    });

    // Aggregation: collect events per-second, flush every second
    let mut buf = Vec::new();
    let mut ticker = interval(Duration::from_secs(1));
    loop {
        tokio::select! {
            Some(evt) = rx.recv() => {
                println!("[Agg] Received trade event from channel: price={}, size={}", evt.price, evt.size);
                buf.push(evt);
            }
            _ = ticker.tick() => {
                println!("[Agg] Aggregation tick; events in buffer: {}", buf.len());
                if buf.is_empty() { continue; }
                // compute OHLCV
                let open = buf[0].price;
                let mut high = open;
                let mut low = open;
                let mut close = open;
                let mut volume = 0.0;
                for e in &buf {
                    high = high.max(e.price);
                    low = low.min(e.price);
                    close = e.price;
                    volume += e.size;
                }
                let bar = Bar {
                    symbol: symbol.clone(),
                    timestamp: Utc::now().to_rfc3339(),
                    open,
                    high,
                    low,
                    close,
                    volume,
                };
                let channel = format!("bars:{}", symbol);
                println!("[Agg] Publishing bar JSON: {}", serde_json::to_string(&bar)?);
                let _: () = redis_conn.publish(channel, serde_json::to_string(&bar)?).await?;
                buf.clear();
            }
        }
    }
} 