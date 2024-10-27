# это БАЗА, для контейнера
FROM python:3.5

RUN apt update
RUN apt upgrade -y

ADD . /testing/testing
WORKDIR /testing/testing

RUN pip install -U pip setuptools wheel
RUN pip install -e .

# меняем настройки подключения к БД
RUN sed -i 's/DATABASE_HOST = localhost/DATABASE_HOST = db/g' app/settings.py

RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh
RUN chmod 777 ./wait-for-it.sh
RUN chmod 777 ./docker-entrypoint.sh

# expose port
EXPOSE 6545

CMD ["./wait-for-it.sh", "db:5432", "--", "./docker-entrypoint.sh"]