FROM python:3.11
ENV APP_HOME /app
ENV PYTHONUNBUFFERED 1
WORKDIR $APP_HOME
COPY requirements.txt .
RUN pip install –no-cache-dir -r requirements.txt

CMD [“python”, “main.py”]