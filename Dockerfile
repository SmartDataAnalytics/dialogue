FROM python:3

ARG MODELSIZE
ARG COREFLANG
ENV R_MODELSIZE=$MODELSIZE
ENV R_COREFLANG=$COREFLANG

ADD requirements.txt /

RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get -y install swi-prolog sfst
RUN git clone https://github.com/lukovnikov/ParZu
RUN cd ParZu/; ./install.sh; python parzu_server.py -p 5000
RUN cd ..
RUN git clone https://github.com/lukovnikov/CorZu
RUN python CorZu/server.py -p 5001 -q 5002

RUN python -m spacy download en
RUN if [ "$MODELSIZE" = "small" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_sm-3.0.0/en_coref_sm-3.0.0.tar.gz ; else echo "no small" ; fi
RUN if [ "$MODELSIZE" = "medium" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_md-3.0.0/en_coref_md-3.0.0.tar.gz ; else echo "no medium" ; fi
RUN if [ "$MODELSIZE" = "large" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_lg-3.0.0/en_coref_lg-3.0.0.tar.gz ; else echo "no large" ; fi

#RUN git clone https://github.com/SmartDataAnalytics/dialogue.git

ADD dialogue /

WORKDIR services/

EXPOSE 8008

CMD python huggin_coref.py -p 8008 -s $R_MODELSIZE -l $R_COREFLANG