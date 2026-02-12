-- Schema para histórico de taxas de câmbio

-- Tabela principal de taxas de câmbio
CREATE TABLE IF NOT EXISTS exchange_rates (
    id SERIAL PRIMARY KEY,
    currency_code VARCHAR(3) NOT NULL,
    rate_to_brl DECIMAL(12, 6) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) DEFAULT 'exchangerate-api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimizar consultas
CREATE INDEX idx_exchange_rates_currency ON exchange_rates(currency_code);
CREATE INDEX idx_exchange_rates_recorded_at ON exchange_rates(recorded_at DESC);
CREATE INDEX idx_exchange_rates_currency_date ON exchange_rates(currency_code, recorded_at DESC);

-- Tabela para rastrear quando as taxas foram atualizadas
CREATE TABLE IF NOT EXISTS rate_updates (
    id SERIAL PRIMARY KEY,
    update_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    currencies_updated INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- View para pegar as taxas mais recentes de cada moeda
CREATE OR REPLACE VIEW latest_rates AS
SELECT DISTINCT ON (currency_code)
    id,
    currency_code,
    rate_to_brl,
    recorded_at
FROM exchange_rates
ORDER BY currency_code, recorded_at DESC;

-- View para estatísticas diárias
CREATE OR REPLACE VIEW daily_rate_stats AS
SELECT 
    currency_code,
    DATE(recorded_at) as date,
    MIN(rate_to_brl) as min_rate,
    MAX(rate_to_brl) as max_rate,
    AVG(rate_to_brl) as avg_rate,
    COUNT(*) as sample_count
FROM exchange_rates
GROUP BY currency_code, DATE(recorded_at)
ORDER BY date DESC, currency_code;

-- Comentários nas tabelas
COMMENT ON TABLE exchange_rates IS 'Histórico completo de taxas de câmbio para BRL';
COMMENT ON TABLE rate_updates IS 'Log de atualizações das taxas de câmbio';
COMMENT ON VIEW latest_rates IS 'Taxas mais recentes para cada moeda';
COMMENT ON VIEW daily_rate_stats IS 'Estatísticas agregadas por dia e moeda';
