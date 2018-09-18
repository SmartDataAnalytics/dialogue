FROM python:3

ARG MODELSIZE
ENV R_MODELSIZE=$MODELSIZE

ADD requirements.txt /

RUN pip install -r requirements.txt

RUN python -m spacy download en
RUN if [ "x$MODELSIZE" = "small" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_sm-3.0.0/en_coref_sm-3.0.0.tar.gz ; else echo "no small" ; fi
RUN if [ "x$MODELSIZE" = "medium" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_sm-3.0.0/en_coref_sm-3.0.0.tar.gz ; else echo "no medium" ; fi
RUN if [ "x$MODELSIZE" = "large" ] ; then pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_lg-3.0.0/en_coref_lg-3.0.0.tar.gz ; else echo "no large" ; fi

RUN git clone https://github.com/SmartDataAnalytics/dialogue.git

WORKDIR dialogue/dialogue/services/

EXPOSE 8008

ENTRYPOINT python huggin_coref.py $R_MODELSIZE 8008