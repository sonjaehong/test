FROM python:3.8.12

WORKDIR /usr/stress
RUN pip install --upgrade pip

COPY requirements.txt ./
COPY setup.py ./

ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir -r requirements.txt

COPY ./ ./

CMD ["python", "mass_req/mass_req.py"]