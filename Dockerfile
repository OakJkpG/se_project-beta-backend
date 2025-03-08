FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=bookhub.settings

RUN python manage.py migrate

EXPOSE 8000

CMD ["gunicorn", "bookhub.wsgi:application", "--bind", "0.0.0.0:8000"]
