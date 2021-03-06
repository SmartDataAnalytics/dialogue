# How to setup this stuff for German

- Install and start ParZu:
  - `sudo apt-get install swi-prolog sfst`
  - `git clone https://github.com/lukovnikov/ParZu`
  - `cd ParZu`
  - `./install.sh`
  - run server by `python parzu_server.py -p <PORT>`
    - `<PORT>` is where this server will be running
- Install and start CorZu (needs Python 2!!):
  - `git clone https://github.com/lukovnikov/CorZu`
  - `cd CorZu`
  - try launching the server (`python server.py`) and install dependencies
  - run server by `python server.py -p <PORT> -q <PARZUPORT>`
    - `<PORT>` is where to run this server
    - `<PARZUPORT>` is where ParZu server is running 
- Install and start this code:
  - `git clone https://github.com/SmartDataAnalytics/dialogue`
  - `cd dialogue`
  - `python setup.py develop`
  - run server by `python dialogue/services/huggin_coref.py -p <PORT> -s <SIZE> -l <LANG>`
    - `<PORT>` is where to start this service
    - `<SIZE>` is one of "small", "medium" or "large" - size of coref model (only makes a difference when `<LANG>` is "en")
    - `<LANG>` is one of "en", "de"
    - in addition, the `EXT_COREF_PORT` environment variable must be set to the port of CorZu (otherwise, default is 5004) 
- Run example code to verify installation:
  - `python dialogue/huggin_coref_user.py <PORT> <LANG>`
    - `<PORT>` is where dialogue coref server is running