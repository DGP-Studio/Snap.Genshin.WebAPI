FROM python:3.9  

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./api-server.py /code/

COPY ./manifesto.txt /code/

COPY ./patch-cache.json /code

COPY ./setting.json /code

CMD ["uvicorn", "api-server:app", "--host", "0.0.0.0", "--port", "8080"]
