-- KAGUJJE Trading Platform Schema
-- Run this in Supabase SQL Editor

-- Broker Accounts (encrypted passwords stored)
CREATE TABLE IF NOT EXISTS broker_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID DEFAULT auth.uid(),
    broker VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    login VARCHAR(100) NOT NULL,
    password TEXT NOT NULL,  -- Will be encrypted
    server VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    balance DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trading Signals
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,  -- 'VOLATILITY', 'FOREX', 'DERIV'
    direction VARCHAR(10) NOT NULL,     -- 'UP', 'DOWN', 'CALL', 'PUT'
    confidence INTEGER DEFAULT 50,
    entry_price DECIMAL(15,5),
    target_price DECIMAL(15,5),
    stop_loss DECIMAL(15,5),
    timeframe VARCHAR(20),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trade History
CREATE TABLE IF NOT EXISTS trade_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id UUID REFERENCES broker_accounts(id),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    lot_size DECIMAL(10,2),
    entry_price DECIMAL(15,5) NOT NULL,
    exit_price DECIMAL(15,5),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    profit DECIMAL(15,2),
    commission DECIMAL(10,2) DEFAULT 0,
    swap DECIMAL(10,2) DEFAULT 0,
    metadata JSONB
);

-- Bot Status
CREATE TABLE IF NOT EXISTS bot_status (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    bot_name VARCHAR(50) UNIQUE NOT NULL,
    is_running BOOLEAN DEFAULT false,
    last_heartbeat TIMESTAMPTZ,
    last_error TEXT,
    stats JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot Commands (for remote control)
CREATE TABLE IF NOT EXISTS bot_commands (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    bot_name VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,  -- 'start', 'stop', 'restart'
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'executed', 'failed'
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot Logs
CREATE TABLE IF NOT EXISTS bot_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    bot_name VARCHAR(50) NOT NULL,
    level VARCHAR(10) NOT NULL,  -- 'info', 'warning', 'error'
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE broker_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_logs ENABLE ROW LEVEL SECURITY;

-- Public read/write policies (adjust for production)
CREATE POLICY "Public access" ON broker_accounts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON trading_signals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON trade_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON bot_status FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON bot_commands FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON bot_logs FOR ALL USING (true) WITH CHECK (true);

-- Insert initial bot status
INSERT INTO bot_status (bot_name, is_running) VALUES
    ('mt5-trader', false),
    ('deriv-signals', false),
    ('kai-learner', false)
ON CONFLICT (bot_name) DO NOTHING;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_signals_created ON trading_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_opened ON trade_history(opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_commands_pending ON bot_commands(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_logs_created ON bot_logs(created_at DESC);
