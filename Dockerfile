# 1. Use uma imagem base oficial do Python
FROM python:3.10-slim

# 2. Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Instala o 'curl' (necessário para o healthcheck) e limpa o cache
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 4. Copie o arquivo de dependências primeiro
COPY requirements.txt requirements.txt

# 5. Instale as dependências
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 6. Copie o conteúdo da pasta src para o diretório de trabalho
COPY ./src .
COPY ./tests ./tests
COPY pytest.ini .

# 7. Exponha a porta que a aplicação vai rodar e a porta de debug
EXPOSE 8080
EXPOSE 5678

# 8. Defina o comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
