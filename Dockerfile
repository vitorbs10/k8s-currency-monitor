# Usa uma imagem leve do Python
FROM python:3.9-slim

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia o seu script para dentro do container
COPY main.py .

# Instala as bibliotecas necessárias
RUN pip install requests prometheus_client

# Comando que o Kubernetes vai executar ao iniciar o container
CMD ["python", "main.py"]
