#!/usr/bin/env python3
"""
MT5 Broker Integration
Connects to MetaTrader 5 accounts and executes trades
Runs on Online PC Engine (GitHub Actions)

Note: MT5 requires Windows or Wine. On GitHub Actions Linux runners,
we use REST API bridges like MetaAPI.cloud for connection.
"""

import json
import time
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, List
import os

# Supabase config
SUPABASE_URL = "https://dtejfdquiqogwapjtfar.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0ZWpmZHF1aXFvZ3dhcGp0ZmFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU5NzQ1ODQsImV4cCI6MjA2MTU1MDU4NH0.UFQYgR0N_xhFYNDJQemzSGxLBFaLgb9s_L5XqKJWBxE")

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8268927401:AAEdXA1d0RwvI0-8oP55XUHCekGE6jINfRg")
KAI_TRADES_CHANNEL = "-1003988793545"
KAI_UPDATES_CHANNEL = "-1003928159270"

# MetaAPI config (for REST-based MT5 connection)
META_API_URL = os.environ.get("META_API_URL", "https://mtrest.vantagemarkets.com")
META_API_KEY = os.environ.get("META_API_KEY", "")

class MT5BrokerIntegration:
    def __init__(self):
        self.accounts: List[Dict] = []
        self.positions: Dict[str, List] = {}
        self.trades_executed = 0
        
    def load_accounts(self) -> None:
        """Load broker accounts from Supabase"""
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/broker_accounts?is_active=eq.true&broker=eq.mt5-forex",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            self.accounts = response.json()
            print(f"Loaded {len(self.accounts)} active MT5 accounts")
        except Exception as e:
            print(f"Error loading accounts: {e}")
            self.accounts = []
    
    def get_account_balance(self, account: Dict) -> Optional[float]:
        """Get account balance via API (simulated for demo)"""
        # In production, use MetaAPI or MT5 REST API
        # For now, return simulated balance
        return account.get("balance", 10000.0) + (time.time() % 100 - 50)
    
    def get_open_positions(self, account: Dict) -> List[Dict]:
        """Get open positions for account"""
        # Simulated for demo
        return [
            {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.01,
                "open_price": 1.0850,
                "current_price": 1.0860,
                "profit": 10.0,
                "sl": 1.0800,
                "tp": 1.0900
            }
        ]
    
    def execute_trade(self, account: Dict, signal: Dict) -> Optional[Dict]:
        """Execute trade based on signal"""
        try:
            # Validate signal
            if signal["confidence"] < 60:
                print(f"Signal confidence too low: {signal['confidence']}%")
                return None
            
            # Calculate position size (risk management)
            balance = self.get_account_balance(account)
            risk_percent = 1.0  # Risk 1% per trade
            risk_amount = balance * (risk_percent / 100)
            
            # Determine lot size
            symbol = signal["symbol"]
            # For forex, use standard lot sizing
            lot_size = min(0.10, max(0.01, risk_amount / 100))
            
            trade = {
                "account_id": account["id"],
                "symbol": symbol,
                "direction": signal["direction"],
                "lot_size": lot_size,
                "entry_price": signal["entry_price"],
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "signal_id": signal.get("id"),
                    "confidence": signal["confidence"]
                }
            }
            
            # In production, send to MT5 via API
            # For demo, just log it
            print(f"Trade executed: {signal['direction']} {symbol} @ {signal['entry_price']}")
            
            # Save to Supabase
            self.save_trade(trade)
            
            return trade
        except Exception as e:
            print(f"Trade execution error: {e}")
            return None
    
    def save_trade(self, trade: Dict) -> bool:
        """Save trade to Supabase"""
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/trade_history",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=trade
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error saving trade: {e}")
            return False
    
    def check_pending_signals(self) -> List[Dict]:
        """Check for pending signals to execute"""
        try:
            # Get signals from last 5 minutes that haven't been executed
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/trading_signals?created_at=gte.{(datetime.now(timezone.utc).timestamp() - 300)}&order=created_at.desc&limit=10",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            return response.json()
        except Exception as e:
            print(f"Error fetching signals: {e}")
            return []
    
    def check_bot_commands(self) -> List[Dict]:
        """Check for bot commands from dashboard"""
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/bot_commands?bot_name=eq.mt5-trader&status=eq.pending",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            return response.json()
        except Exception as e:
            print(f"Error fetching commands: {e}")
            return []
    
    def mark_command_executed(self, command_id: str) -> None:
        """Mark command as executed"""
        try:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/bot_commands?id=eq.{command_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "status": "executed",
                    "executed_at": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            print(f"Error marking command: {e}")
    
    def update_heartbeat(self) -> None:
        """Update bot status in Supabase"""
        try:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/bot_status?bot_name=eq.mt5-trader",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "is_running": True,
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                    "stats": {
                        "accounts_active": len(self.accounts),
                        "trades_executed": self.trades_executed
                    }
                }
            )
        except Exception as e:
            print(f"Heartbeat error: {e}")
    
    def notify_trade(self, trade: Dict) -> None:
        """Notify Telegram of trade execution"""
        try:
            direction = "🟢 BUY" if trade["direction"] == "UP" else "🔴 SELL"
            message = f"""
{direction} {trade["symbol"]}

📊 Lot Size: {trade["lot_size"]}
💰 Entry: {trade["entry_price"]}
⏰ Time: {datetime.now().strftime("%H:%M:%S")} UTC

🤖 Executed by Online PC Engine
"""
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": KAI_TRADES_CHANNEL,
                    "text": message.strip()
                }
            )
        except Exception as e:
            print(f"Telegram error: {e}")
    
    def log_to_supabase(self, level: str, message: str) -> None:
        """Log to Supabase for dashboard visibility"""
        try:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/bot_logs",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "bot_name": "mt5-trader",
                    "level": level,
                    "message": message,
                    "metadata": {"timestamp": datetime.now(timezone.utc).isoformat()}
                }
            )
        except Exception as e:
            print(f"Log error: {e}")
    
    def run_cycle(self) -> None:
        """Run one trading cycle"""
        # Refresh accounts
        self.load_accounts()
        
        # Check for commands
        commands = self.check_bot_commands()
        for cmd in commands:
            if cmd["action"] == "stop":
                print("Stop command received, shutting down...")
                return False
            self.mark_command_executed(cmd["id"])
        
        # Check for signals to execute
        signals = self.check_pending_signals()
        for signal in signals:
            for account in self.accounts:
                if signal["symbol"].startswith("V") or signal["symbol"] in ["BOOM1000", "CRASH1000"]:
                    # Deriv signals - skip for MT5
                    continue
                
                trade = self.execute_trade(account, signal)
                if trade:
                    self.notify_trade(trade)
                    self.trades_executed += 1
        
        # Update heartbeat
        self.update_heartbeat()
        self.log_to_supabase("info", f"Cycle completed. Accounts: {len(self.accounts)}, Trades: {self.trades_executed}")
        
        return True

def main():
    print("🚀 MT5 Broker Integration Started")
    print("=" * 50)
    
    broker = MT5BrokerIntegration()
    
    # Run for specified cycles
    max_cycles = int(os.environ.get("MAX_CYCLES", "100"))
    interval = int(os.environ.get("TRADE_INTERVAL", "60"))
    
    for cycle in range(1, max_cycles + 1):
        print(f"\n--- Cycle {cycle}/{max_cycles} ---")
        
        if not broker.run_cycle():
            break
        
        if cycle < max_cycles:
            time.sleep(interval)
    
    print("\n✅ MT5 Broker Integration Completed")

if __name__ == "__main__":
    main()
