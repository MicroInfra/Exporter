FROM python:3.11
WORKDIR /app
COPY ./requirements.txt .
RUN pip3 install -r ./requirements.txt

COPY . .
EXPOSE 62933
CMD ["uwsgi --http 0.0.0.0:62933 --wsgi-file app.py --callable app"]
