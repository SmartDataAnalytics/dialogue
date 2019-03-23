#!/usr/bin/env bash

python ../../ParZu/parzu_server.py -p 6500 &
python ../../CorZu/server.py -p 6501 -q 6500 &
python coref.py -p 8008 -s $R_MODELSIZE