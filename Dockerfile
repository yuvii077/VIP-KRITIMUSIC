FROM nikolaik/python-nodejs:python3.10-nodejs20

# System updates
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg aria2 git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/

# Pip ko upgrade karna aur dependencies install karna
# Isse "Do you want to upgrade (y/n)" wala jhamela khatam ho jayega
RUN python -m pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir .

# Seedha bot ko start karein, kisi script (.sh) ke chakkar mein na padein
CMD python3 -m VIPMUSIC
