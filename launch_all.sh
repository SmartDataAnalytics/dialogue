#!/usr/bin/env bash

python ../../ParZu/parzu_server.py -p 5000 &
python ../../CorZu/server.py -p 5001 -q 5000 &
python coref.py -p 8008 -s $R_MODELSIZE