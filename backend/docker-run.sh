#!/bin/sh

#docker run -d \

docker run -it --entrypoint /bin/bash \
  -p 8044:8044 \
  --env-file .env \
  -v ./db:/app/backend/db \
  -v ./logs:/app/backend/logs \
  --name be01 panzim-be:0.0.1
