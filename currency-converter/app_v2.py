from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
from dateutil import parser
import os
import logging
from database import DatabaseManager

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Cache para taxas de câmbio
cache = {
    'rates': {},
    'last_update': None
}

SUPPORTED_CURRENCIES = ['USD', 'EUR', 'CAD', 'CHF', 'GBP', 'JPY', 'CNY']
CACHE_DURATION_MINUTES = 30

# Inicializa o banco de dados
db = DatabaseManager()

def update_exchange_rates():
    """Atualiza as taxas de câmbio usando API e salva no banco"""
    try:
        # Usando exchangerate-api (gratuita)
        api_key = os.environ.get('EXCHANGE_API_KEY', 'demo')
        url = f"https://api.exchangerate-api.com/v4/latest/BRL"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Inverter as taxas (queremos de moeda estrangeira para BRL)
        rates = {}
        for currency in SUPPORTED_CURRENCIES:
            if currency in data['rates']:
                # Taxa inversa (de moeda estrangeira para BRL)
                rates[currency] = 1 / data['rates'][currency]
        
        # Atualiza cache
        cache['rates'] = rates
        cache['last_update'] = datetime.now()
        
        # Salva no banco de dados
        db.save_rates(rates)
        
        app.logger.info(f"Taxas atualizadas com sucesso: {rates}")
        return True
    except Exception as e:
        app.logger.error(f"Erro ao atualizar taxas: {str(e)}")
        return False

def get_cached_rates():
    """Retorna taxas do cache ou atualiza se necessário"""
    now = datetime.now()
    
    if not cache['rates'] or not cache['last_update']:
        update_exchange_rates()
    elif (now - cache['last_update']) > timedelta(minutes=CACHE_DURATION_MINUTES):
        update_exchange_rates()
    
    return cache['rates']

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check para Kubernetes"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'rates_available': len(cache['rates']) > 0,
        'database_connected': db.ensure_connection()
    }), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Endpoint de readiness para Kubernetes"""
    if cache['rates'] and db.ensure_connection():
        return jsonify({'status': 'ready'}), 200
    else:
        return jsonify({'status': 'not ready'}), 503

@app.route('/rates', methods=['GET'])
def get_rates():
    """Retorna todas as taxas de câmbio atuais (moeda estrangeira -> BRL)"""
    rates = get_cached_rates()
    
    return jsonify({
        'base_currency': 'BRL',
        'rates': rates,
        'last_update': cache['last_update'].isoformat() if cache['last_update'] else None,
        'supported_currencies': SUPPORTED_CURRENCIES
    }), 200

@app.route('/rates/latest', methods=['GET'])
def get_latest_rates_from_db():
    """Retorna as taxas mais recentes do banco de dados"""
    rates = db.get_latest_rates()
    
    return jsonify({
        'base_currency': 'BRL',
        'rates': rates,
        'supported_currencies': SUPPORTED_CURRENCIES
    }), 200

@app.route('/convert', methods=['GET'])
def convert_currency():
    """
    Converte valor de uma moeda estrangeira para BRL
    Parâmetros:
    - from: código da moeda (USD, EUR, etc)
    - amount: valor a converter
    
    Exemplo: /convert?from=USD&amount=100
    """
    from_currency = request.args.get('from', '').upper()
    amount_str = request.args.get('amount', '0')
    
    try:
        amount = float(amount_str)
    except ValueError:
        return jsonify({'error': 'Valor inválido'}), 400
    
    if from_currency not in SUPPORTED_CURRENCIES:
        return jsonify({
            'error': f'Moeda não suportada. Moedas disponíveis: {SUPPORTED_CURRENCIES}'
        }), 400
    
    rates = get_cached_rates()
    
    if from_currency not in rates:
        return jsonify({'error': 'Taxa de câmbio não disponível'}), 503
    
    rate = rates[from_currency]
    converted_amount = amount * rate
    
    return jsonify({
        'from_currency': from_currency,
        'to_currency': 'BRL',
        'original_amount': amount,
        'converted_amount': round(converted_amount, 2),
        'exchange_rate': round(rate, 4),
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/convert/reverse', methods=['GET'])
def convert_currency_reverse():
    """
    Converte valor de BRL para moeda estrangeira
    Parâmetros:
    - to: código da moeda (USD, EUR, etc)
    - amount: valor em BRL a converter
    
    Exemplo: /convert/reverse?to=USD&amount=100
    """
    to_currency = request.args.get('to', '').upper()
    amount_str = request.args.get('amount', '0')
    
    try:
        amount = float(amount_str)
    except ValueError:
        return jsonify({'error': 'Valor inválido'}), 400
    
    if to_currency not in SUPPORTED_CURRENCIES:
        return jsonify({
            'error': f'Moeda não suportada. Moedas disponíveis: {SUPPORTED_CURRENCIES}'
        }), 400
    
    rates = get_cached_rates()
    
    if to_currency not in rates:
        return jsonify({'error': 'Taxa de câmbio não disponível'}), 503
    
    rate = rates[to_currency]
    converted_amount = amount / rate
    
    return jsonify({
        'from_currency': 'BRL',
        'to_currency': to_currency,
        'original_amount': amount,
        'converted_amount': round(converted_amount, 2),
        'exchange_rate': round(1/rate, 4),
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/history/<currency_code>', methods=['GET'])
def get_historical_rates(currency_code):
    """
    Retorna histórico de taxas para uma moeda
    Parâmetros:
    - start_date: data inicial (formato: YYYY-MM-DD)
    - end_date: data final (formato: YYYY-MM-DD)
    
    Exemplo: /history/USD?start_date=2024-02-01&end_date=2024-02-10
    """
    currency_code = currency_code.upper()
    
    if currency_code not in SUPPORTED_CURRENCIES:
        return jsonify({
            'error': f'Moeda não suportada. Moedas disponíveis: {SUPPORTED_CURRENCIES}'
        }), 400
    
    # Parse dates
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    try:
        if start_date_str:
            start_date = parser.parse(start_date_str)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        if end_date_str:
            end_date = parser.parse(end_date_str)
        else:
            end_date = datetime.now()
    except Exception as e:
        return jsonify({'error': f'Formato de data inválido: {str(e)}'}), 400
    
    history = db.get_historical_rates(currency_code, start_date, end_date)
    
    return jsonify({
        'currency_code': currency_code,
        'base_currency': 'BRL',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'data_points': len(history),
        'history': history
    }), 200

@app.route('/stats/<currency_code>', methods=['GET'])
def get_currency_stats(currency_code):
    """
    Retorna estatísticas diárias para uma moeda
    Parâmetros:
    - days: número de dias (padrão: 30)
    
    Exemplo: /stats/USD?days=7
    """
    currency_code = currency_code.upper()
    
    if currency_code not in SUPPORTED_CURRENCIES:
        return jsonify({
            'error': f'Moeda não suportada. Moedas disponíveis: {SUPPORTED_CURRENCIES}'
        }), 400
    
    days = request.args.get('days', 30, type=int)
    
    if days < 1 or days > 365:
        return jsonify({'error': 'Dias deve estar entre 1 e 365'}), 400
    
    stats = db.get_daily_stats(currency_code, days)
    
    return jsonify({
        'currency_code': currency_code,
        'base_currency': 'BRL',
        'days_requested': days,
        'days_available': len(stats),
        'stats': stats
    }), 200

@app.route('/rate-at-date/<currency_code>', methods=['GET'])
def get_rate_at_specific_date(currency_code):
    """
    Retorna a taxa de uma moeda em uma data específica
    Parâmetros:
    - date: data desejada (formato: YYYY-MM-DD)
    
    Exemplo: /rate-at-date/USD?date=2024-02-01
    """
    currency_code = currency_code.upper()
    
    if currency_code not in SUPPORTED_CURRENCIES:
        return jsonify({
            'error': f'Moeda não suportada. Moedas disponíveis: {SUPPORTED_CURRENCIES}'
        }), 400
    
    date_str = request.args.get('date')
    
    if not date_str:
        return jsonify({'error': 'Parâmetro date é obrigatório'}), 400
    
    try:
        target_date = parser.parse(date_str)
    except Exception as e:
        return jsonify({'error': f'Formato de data inválido: {str(e)}'}), 400
    
    rate_data = db.get_rate_at_date(currency_code, target_date)
    
    if not rate_data:
        return jsonify({
            'error': f'Nenhuma taxa encontrada para {currency_code} em {date_str}'
        }), 404
    
    return jsonify({
        'currency_code': currency_code,
        'base_currency': 'BRL',
        'requested_date': target_date.date().isoformat(),
        'rate': rate_data['rate'],
        'recorded_at': rate_data['recorded_at']
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Endpoint raiz com informações da API"""
    return jsonify({
        'service': 'Currency Converter API',
        'version': '2.0.0',
        'features': ['Real-time rates', 'Historical data', 'Daily statistics'],
        'endpoints': {
            '/health': 'Health check',
            '/ready': 'Readiness check',
            '/rates': 'Get current exchange rates (cached)',
            '/rates/latest': 'Get latest rates from database',
            '/convert?from=USD&amount=100': 'Convert foreign currency to BRL',
            '/convert/reverse?to=USD&amount=100': 'Convert BRL to foreign currency',
            '/history/USD?start_date=2024-02-01&end_date=2024-02-10': 'Get historical rates',
            '/stats/USD?days=30': 'Get daily statistics',
            '/rate-at-date/USD?date=2024-02-01': 'Get rate at specific date'
        },
        'supported_currencies': SUPPORTED_CURRENCIES
    }), 200

if __name__ == '__main__':
    # Atualiza taxas na inicialização
    update_exchange_rates()
    
    # Roda o servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
