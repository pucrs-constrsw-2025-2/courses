# 1. Use uma imagem base oficial do Python
FROM python:3.10-slim

# 2. Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Copie o arquivo de dependências primeiro (para aproveitar o cache do Docker)
COPY requirements.txt requirements.txt

# 4. Instale as dependências
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 5. Copie o resto do código da sua aplicação para o diretório de trabalho
COPY . .

# 6. Exponha a porta que a aplicação vai rodar dentro do contêiner
EXPOSE 8000

# 7. Defina o comando para iniciar a aplicação quando o contêiner for executado
# O host 0.0.0.0 é crucial para que a aplicação seja acessível de fora do contêiner
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]