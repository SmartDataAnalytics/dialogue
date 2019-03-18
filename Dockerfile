FROM python:3

ARG MODELSIZE
ENV R_MODELSIZE=$MODELSIZE

ADD requirements.txt /

RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get -y install swi-prolog sfst
RUN git clone https://github.com/lukovnikov/ParZu
RUN cd ParZu/; ./install.sh
RUN python ParZu/parzu_server.py -p 5000 &
RUN git clone https://github.com/lukovnikov/CorZu
RUN export EXT_COREF_PORT=5001

RUN python -m spacy download en
RUN if [ "$MODELSIZE" = "small" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_sm-3.0.0/en_coref_sm-3.0.0.tar.gz ; else echo "no small" ; fi
RUN if [ "$MODELSIZE" = "medium" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_md-3.0.0/en_coref_md-3.0.0.tar.gz ; else echo "no medium" ; fi
RUN if [ "$MODELSIZE" = "large" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_lg-3.0.0/en_coref_lg-3.0.0.tar.gz ; else echo "no large" ; fi

#RUN git clone https://github.com/SmartDataAnalytics/dialogue.git

ADD . /
RUN python setup.py develop

WORKDIR dialogue/services/

EXPOSE 8008

RUN python ../../ParZu/parzu_server.py -p 5000 &
RUN python ../../CorZu/server.py -p 5001 -q 5000 &
CMD python coref.py -p 8008 -s $R_MODELSIZE