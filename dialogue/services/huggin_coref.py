#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Coreference resolution server from Hugging Face.
"""
from __future__ import unicode_literals
from __future__ import print_function

import json
from wsgiref.simple_server import make_server
import falcon
import spacy
import sys

try:
    unicode_ = unicode  # Python 2
except NameError:
    unicode_ = str      # Python 3


def get_dict_of_span(span):
    ret = {}
    ret["start_char"] = span.start_char
    ret["end_char"] = span.end_char
    ret["start"] = span.start
    ret["end"] = span.end
    ret["text"] = span.text
    return ret


class AllResource(object):
    def __init__(self, model_size):
        if model_size == "small":
            model = "en_coref_sm"
        elif model_size == "medium":
            model = "en_coref_md"
        elif model_size == "large":
            model = "en_coref_lg"
        else:
            raise Exception("specified invalid model size: {}. Must be one of 'small', 'medium', 'large'"
                            .format(model_size))
        self.nlp = spacy.load(model)
        print("Server loaded")
        self.response = None

    def on_get(self, req, resp):
        self.response = {}

        text_param = req.get_param("text")
        if text_param is not None:
            text = ",".join(text_param) if isinstance(text_param, list) else text_param
            text = unicode_(text)
            doc = self.nlp(text)
            if doc._.has_coref:
                clusters = []
                # mentions = [{'start':    span.start_char,
                #              'end':      span.end_char,
                #              'text':     span.text,
                #              'resolved': span._.coref_main_mention.text
                #             } for span in doc._.coref_mentions]
                # clusters = list(list(span.text for span in cluster)
                #                 for cluster in doc._.coref_clusters)
                for cluster in doc._.coref_clusters:
                    _cluster = {}
                    main = cluster.main
                    _cluster["main"] = get_dict_of_span(main)
                    _cluster["mentions"] = []
                    for mention in cluster.mentions:
                        _cluster["mentions"].append(get_dict_of_span(mention))
                    clusters.append(_cluster)
                resolved = doc._.coref_resolved
                # self.response['mentions'] = mentions
                self.response['clusters'] = clusters
                self.response['resolved'] = resolved
                self.response['tokens'] = [str(token) for token in doc]

        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200


if __name__ == '__main__':
    port = int(sys.argv[1])
    size = str(sys.argv[2])
    RESSOURCE = AllResource(size)
    APP = falcon.API()
    APP.add_route('/', RESSOURCE)
    HTTPD = make_server('0.0.0.0', port, APP)
    HTTPD.serve_forever()