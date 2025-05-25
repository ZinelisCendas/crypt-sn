FROM python:3.12-slim
RUN apt-get update && apt-get install -y build-essential libssl-dev
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
