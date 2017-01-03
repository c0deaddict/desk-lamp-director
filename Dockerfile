FROM python:3-alpine
WORKDIR /
COPY main.py ./
COPY requirements.txt ./
RUN pip install -r requirements.txt
CMD ["/usr/local/bin/python", "/main.py"]
