FROM nikolaik/python-nodejs:python3.11-nodejs22

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg aria2 git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/

# Pip upgrade aur direct dependency install
RUN python -m pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -U -r requirements.txt || pip install --no-cache-dir .

CMD python3 -m VIPMUSIC
