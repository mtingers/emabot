# WIP: hasn't really been tested but might work?
# Probably need a volume to mount etc and data dirs (maybe log too)
FROM python:3.9
WORKDIR /app
ADD . .
RUN ls -laF
RUN apt-get update
RUN apt-get install gcc g++ make vim -y
RUN cd talib/ && tar -xzf ta-lib-0.4.0-src.tar.gz
RUN cd talib/ta-lib && ./configure --prefix=/usr && make && make install
RUN pip install pip -U
RUN pip install .
