FROM alpine:3.11

# Basics
RUN apk update
RUN apk upgrade
RUN apk add g++ gcc git freetype freetype-dev fontconfig fontconfig-dev libffi-dev make python3 python3-dev py3-pip cmake

WORKDIR /opt/font-assets

# OpenLL Asset Generator

RUN git clone https://github.com/cginternals/openll-asset-generator.git

WORKDIR /opt/font-assets/openll-asset-generator

RUN mkdir build

WORKDIR /opt/font-assets/openll-asset-generator/build
RUN cmake .. -DCMAKE_BUILD_TYPE=Release -DOPTION_BUILD_TESTS=Off
RUN make

WORKDIR /opt/font-assets

# Service

ADD requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

# FastAPI, ASGI deployment
# RUN pip install fastapi uvicorn celery
# RUN pip install python-multipart aiofiles
# RUN pip3 freeze

# Deploy
# COPY bin bin
ADD . service

ENV USERNAME=font-assets-service
ENV LLASSETGEN_DIRECTORY=/opt/font-assets/openll-asset-generator/build
ENV RESULT_DIR=/data/results

# CMD ["uvicorn", "--host=0.0.0.0", "main:app"]
CMD ["python3", "service/main.py"]
