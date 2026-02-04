#!/bin/sh

docker run -d \
  -p 8044:8044 \
  -v $(pwd)/db:/app/db \
  -v $(pwd)/logs:/app/logs \
  --name panzim-be \
  panzim-be-1.0.2
