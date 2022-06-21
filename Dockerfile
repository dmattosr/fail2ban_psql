FROM python:3.10
RUN apt-get update && apt-get -y install cron vim
WORKDIR /app
COPY crontab /etc/cron.d/crontab
COPY run.py /app/run.py
COPY app.env /app/app.env
COPY requirements.txt /app/requirements.txt
RUN chmod 0644 /etc/cron.d/crontab
RUN wget https://cdn.jsdelivr.net/npm/geolite2-city@1.0.2/GeoLite2-City.mmdb.gz
RUN gunzip GeoLite2-City.mmdb.gz
RUN /usr/bin/crontab /etc/cron.d/crontab
RUN pip install -r /app/requirements.txt
CMD ["cron", "-f"]
