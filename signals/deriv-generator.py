#!/usr/bin/env python3
"""
Deriv Volatility Index Signal Generator
Generates trading signals for Deriv Volatility indices
Runs on Online PC Engine (GitHub Actions)

Strategy: RSI + Bollinger Bands + Momentum
- Volatility 10 (1s): Fast scalping
- Volatility 75 (1s): Medium volatility
- Volatility 100 (1s): High volatility
- Volatility 100 (1s) Boom & Crash
"""

import json
import time
import random
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, List

# Supabase config
SUPABASE_URL = "https://dtejfdquiqogwapjtfar.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0ZWpmZHF1aXFvZ3dhcGp0ZmFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU5NzQ1ODQsImV4cCI6MjA2MTU1MDU4NH0.UFQYgR0N_xhFYNDJQemzSGxLBFaLgb9s_L5XqKJWBxE"

# Telegram config
TELEGRAM_BOT_TOKEN = "8268927401:AAEdXA1d0RwvI0-8oP55XUHCekGE6jINfRg"
KAI_TRADES_CHANNEL = "-1003988793545"

# Volatility indices
SYMBOLS = {
    "V10": "Volatility 10 (1s)",
    "V25": "Volatility 25 (1s)",
    "V50": "Volatility 50 (1s)",
    "V75": "Volatility 75 (1s)",
    "V100": "Volatility 100 (1s)",
    "BOOM1000": "Boom 1000 Index",
    "CRASH1000": "Crash 1000 Index",
}

class SignalGenerator:
    def __init__(self):
        self.price_history: Dict[str, List[float]] = {sym: [] for sym in SYMBOLS}
        self.signals_sent = 0
        
    def update_price(self, symbol: str, price: float) -> None:
        """Update price history for analysis"""
        self.price_history[symbol].append(price)
        # Keep last 100 prices
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d for d in deltas[-period:] if d > 0]
        losses = [-d for d in deltas[-period:] if d < 0]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_bollinger(self, prices: List[float], period: int = 20) -> Optional[Dict]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None
        
        recent = prices[-period:]
        sma = sum(recent) / period
        variance = sum((p - sma) ** 2 for p in recent) / period
        std = variance ** 0.5
        
        return {
            "middle": sma,
            "upper": sma + (2 * std),
            "lower": sma - (2 * std),
            "width": std * 4  # Band width
        }
    
    def calculate_momentum(self, prices: List[float], period: int = 10) -> Optional[float]:
        """Calculate price momentum"""
        if len(prices) < period + 1:
            return None
        return prices[-1] - prices[-period]
    
    def generate_signal(self, symbol: str) -> Optional[Dict]:
        """Generate trading signal based on indicators"""
        prices = self.price_history[symbol]
        
        if len(prices) < 30:
            return None
        
        rsi = self.calculate_rsi(prices)
        bb = self.calculate_bollinger(prices)
        momentum = self.calculate_momentum(prices)
        
        if not all([rsi, bb, momentum]):
            return None
        
        current_price = prices[-1]
        
        signal = None
        confidence = 50
        
        # Oversold condition (RSI < 30, price below lower BB, negative momentum slowing)
        if rsi < 35 and current_price < bb["lower"] and momentum > -0.5:
            signal = "UP"
            confidence = min(85, 60 + (35 - rsi) * 2)
        
        # Overbought condition (RSI > 70, price above upper BB, positive momentum slowing)
        elif rsi > 65 and current_price > bb["upper"] and momentum < 0.5:
            signal = "DOWN"
            confidence = min(85, 60 + (rsi - 65) * 2)
        
        # Boom/Crash specific logic
        if symbol in ["BOOM1000", "CRASH1000"]:
            # Boom: Wait for spike detection
            if symbol == "BOOM1000" and momentum > 2:
                signal = "DOWN"
                confidence = 75
            
            # Crash: Wait for spike detection
            elif symbol == "CRASH1000" and momentum < -2:
                signal = "UP"
                confidence = 75
        
        if signal:
            return {
                "symbol": symbol,
                "signal_type": "DERIV",
                "direction": signal,
                "confidence": confidence,
                "entry_price": current_price,
                "timeframe": "1s",
                "metadata": {
                    "rsi": round(rsi, 2),
                    "bb_upper": round(bb["upper"], 4),
                    "bb_lower": round(bb["lower"], 4),
                    "momentum": round(momentum, 4)
                }
            }
        
        return None
    
    def save_signal(self, signal: Dict) -> bool:
        """Save signal to Supabase"""
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/trading_signals",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=signal
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error saving signal: {e}")
            return False
    
    def notify_telegram(self, signal: Dict) -> bool:
        """Send signal to Telegram channel"""
        try:
            direction_emoji = "📈 CALL" if signal["direction"] == "UP" else "📉 PUT"
            message = f"""
{direction_emoji} {SIGNALS.get(signal["symbol"], signal["symbol"])}

🎯 Signal: {signal["direction"]}
📊 Confidence: {signal["confidence"]}%
💰 Entry: {signal["entry_price"]:.4f}

⏱️ Time: {datetime.now(timezone.utc).strftime("%H:%M:%S")} UTC
🤖 Generated by Online PC Engine

RSI: {signal["metadata"]["rsi"]}
BB: {signal["metadata"]["bb_lower"]:.4f} - {signal["metadata"]["bb_upper"]:.4f}
"""
            
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": KAI_TRADES_CHANNEL,
                    "text": message.strip(),
                    "parse_mode": "HTML"
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def update_heartbeat(self) -> None:
        """Update bot status in Supabase"""
        try:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/bot_status?bot_name=eq.deriv-signals",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "is_running": True,
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                    "stats": {
                        "signals_sent": self.signals_sent,
                        "symbols_active": len([s for s in self.price_history if self.price_history[s]])
                    }
                }
            )
        except Exception as e:
            print(f"Heartbeat error: {e}")
    
    def simulate_market_data(self) -> None:
        """Simulate market data for testing (replace with real API in production)"""
        for symbol in SYMBOLS:
            # Generate realistic price movements
            base_prices = {
                "V10": 1000.0,
                "V25": 1000.0,
                "V50": 1000.0,
                "V75": 1000.0,
                "V100": 1000.0,
                "BOOM1000": 1000.0,
                "CRASH1000": 1000.0,
            }
            
            base = base_prices.get(symbol, 1000.0)
            volatility = {
                "V10": 0.1,
                "V25": 0.25,
                "V50": 0.5,
                "V75": 0.75,
                "V100": 1.0,
                "BOOM1000": 0.3,
                "CRASH1000": 0.3,
            }.get(symbol, 0.5)
            
            # Random walk with volatility
            if self.price_history[symbol]:
                last = self.price_history[symbol][-1]
                change = random.gauss(0, volatility) * 0.01 * last
                # Occasionally add spikes for Boom/Crash
                if symbol in ["BOOM1000", "CRASH1000"] and random.random() < 0.02:
                    spike = random.uniform(5, 15) * (1 if symbol == "BOOM1000" else -1)
                    change += spike
                new_price = last + change
            else:
                new_price = base
            
            self.update_price(symbol, new_price)
    
    def run_cycle(self) -> None:
        """Run one signal generation cycle"""
        self.simulate_market_data()
        
        for symbol in SYMBOLS:
            signal = self.generate_signal(symbol)
            if signal:
                if self.save_signal(signal):
                    self.notify_telegram(signal)
                    self.signals_sent += 1
                    print(f"[{datetime.now()}] Signal: {symbol} {signal['direction']} ({signal['confidence']}%)")
        
        self.update_heartbeat()

def main():
    print("🚀 Deriv Signal Generator Started")
    print("=" * 50)
    
    generator = SignalGenerator()
    
    # Run for specified cycles
    max_cycles = int(os.environ.get("MAX_CYCLES", "100"))
    interval = int(os.environ.get("SIGNAL_INTERVAL", "60"))
    
    for cycle in range(1, max_cycles + 1):
        print(f"\n--- Cycle {cycle}/{max_cycles} ---")
        generator.run_cycle()
        
        if cycle < max_cycles:
            time.sleep(interval)
    
    print("\n✅ Signal Generator Completed")

if __name__ == "__main__":
    import os
    main()
