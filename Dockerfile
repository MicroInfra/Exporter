FROM python:3.11
WORKDIR /app
COPY . .
RUN pip3 install -r ./requirements.txt

EXPOSE 60123
CMD ["uwsgi", "--http", "0.0.0.0:60123", "--wsgi-file", "app.py", "--callable", "app"]
