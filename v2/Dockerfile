FROM python

WORKDIR /app

COPY requirements.txt /app

RUN pip install -r requirements.txt

COPY requester.py /app

EXPOSE 80

CMD requester.py