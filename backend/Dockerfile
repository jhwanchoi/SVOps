FROM python:3.9-slim

WORKDIR /app

# SSL 인증서 문제 해결을 위한 설정
RUN pip config set global.trusted-host pypi.org
RUN pip config set global.trusted-host pypi.python.org
RUN pip config set global.trusted-host files.pythonhosted.org

COPY requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]