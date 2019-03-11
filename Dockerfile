FROM python:3

ARG MODELSIZE
ENV R_MODELSIZE=$MODELSIZE

ADD requirements.txt /

RUN apt-get install swi-prolog sfst
RUN git clone https://github.com/lukovnikov/ParZu
RUN ParZu/install.sh
RUN python ParZu/parzu_server.py -p 5000
RUN pip install -r requirements.txt

RUN python -m spacy download en
RUN if [ "$MODELSIZE" = "small" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_sm-3.0.0/en_coref_sm-3.0.0.tar.gz ; else echo "no small" ; fi
RUN if [ "$MODELSIZE" = "medium" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_md-3.0.0/en_coref_md-3.0.0.tar.gz ; else echo "no medium" ; fi
RUN if [ "$MODELSIZE" = "large" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_lg-3.0.0/en_coref_lg-3.0.0.tar.gz ; else echo "no large" ; fi

#RUN git clone https://github.com/SmartDataAnalytics/dialogue.git

ADD dialogue /

WORKDIR services/

EXPOSE 8008

CMD python huggin_coref.py 8008 $R_MODELSIZE