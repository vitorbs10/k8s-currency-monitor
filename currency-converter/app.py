from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Cache para taxas de câmbio
cache = {
    'rates': {},
    'last_update': None
}

SUPPORTED_CURRENCIES = ['USD', 'EUR', 'CAD', 'CHF', 'GBP', 'JPY', 'CNY']
CACHE_DURATION_MINUTES = 30

def update_exchange_rates():
    """Atualiza as taxas de câmbio usando API gratuita"""
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
        
        cache['rates'] = rates
        cache['last_update'] = datetime.now()
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
        'rates_available': len(cache['rates']) > 0
    }), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Endpoint de readiness para Kubernetes"""
    if cache['rates']:
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

@app.route('/', methods=['GET'])
def root():
    """Endpoint raiz com informações da API"""
    return jsonify({
        'service': 'Currency Converter API',
        'version': '1.0.0',
        'endpoints': {
            '/health': 'Health check',
            '/ready': 'Readiness check',
            '/rates': 'Get all exchange rates',
            '/convert?from=USD&amount=100': 'Convert foreign currency to BRL',
            '/convert/reverse?to=USD&amount=100': 'Convert BRL to foreign currency'
        },
        'supported_currencies': SUPPORTED_CURRENCIES
    }), 200

if __name__ == '__main__':
    # Atualiza taxas na inicialização
    update_exchange_rates()
    
    # Roda o servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
