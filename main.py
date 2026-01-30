import requests
import time
from prometheus_client import start_http_server, Gauge

# 1. Definimos o que o Prometheus vai "anotar"
# Criamos uma métrica chamada 'preco_moeda' com uma etiqueta 'simbolo'
PRECO_MOEDA = Gauge('preco_moeda_atual', 'Preço atual da moeda em BRL', ['simbolo'])

def busca_precos():
    # API pública e gratuita que não exige cadastro
    url = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL,BTC-BRL"
    
    try:
        response = requests.get(url)
        dados = response.json()

        # Extraindo os valores da resposta da API
        usd = float(dados['USDBRL']['bid'])
        eur = float(dados['EURBRL']['bid'])
        btc = float(dados['BTCBRL']['bid'])

        # 2. Enviando os valores para o coletor do Prometheus
        PRECO_MOEDA.labels(simbolo='USD').set(usd)
        PRECO_MOEDA.labels(simbolo='EUR').set(eur)
        PRECO_MOEDA.labels(simbolo='BTC').set(btc)

        print(f"Dados coletados: USD:{usd}, EUR:{eur}, BTC:{btc}")

    except Exception as e:
        print(f"Erro ao buscar dados: {e}")

if __name__ == '__main__':
    # 3. O App abre uma "página" na porta 8000 para o Prometheus ler
    start_http_server(8000)
    print("Servidor de métricas rodando na porta 8000...")
    
    while True:
        busca_precos()
        time.sleep(30) # Espera 30 segundos para a próxima busca
