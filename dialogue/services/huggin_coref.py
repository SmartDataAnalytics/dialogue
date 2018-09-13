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
import re

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


class ClusterResource(object):
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

    def get_clusters(self, text):
        response = {}
        if text is not None:
            text = ",".join(text) if isinstance(text, list) else text
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
                response['clusters'] = clusters
                response['resolved'] = resolved
                response['tokens'] = [str(token) for token in doc]
        return response

    def on_get(self, req, resp):
        text_param = req.get_param("text")
        self.response = self.get_clusters(text_param)
        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200


class GetCorefResource(object):
    def __init__(self, clusterer):
        super(GetCorefResource, self).__init__()
        self.clusterer = clusterer
        self.response = None

    def on_get(self, req, resp):
        context = req.get_param("context")
        sentence = req.get_param("sentence")
        self.response = {}
        context, sentence, context_tokens, sentence_tokens, refs = self.get_corefs(context, sentence)
        self.response["context"] = context
        self.response["sentence"] = sentence
        self.response["context_tokens"] = context_tokens
        self.response["sentence_tokens"] = sentence_tokens
        self.response["references"] = refs
        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200

    def get_corefs(self, context, sentence):
        text = context + " --- " + sentence
        clusters = self.clusterer.get_clusters(text)
        # get tokens of sentence
        tokens = clusters["tokens"]
        i = 0
        while i < len(tokens):
            if tokens[i] == "---":
                break
            i += 1
        sentence_start = i
        i = 0
        while i < len(text) - 5:
            if text[i:i+5] == " --- ":
                break
            i += 1
        sentence_start_char = i

        context_tokens = tokens[:sentence_start]
        sentence_tokens = tokens[sentence_start+1:]
        context = text[:sentence_start_char]
        sentence = text[sentence_start_char+5:]
        references = []
        for cluster in clusters["clusters"]:
            cluster_mention = None
            for mention in cluster["mentions"]:
                if mention["start"] >= sentence_start:
                    cluster_mention = mention
                    break
            if cluster_mention is not None:
                # mentioned in sentence !
                reference = {"from": {"text": cluster_mention["text"],
                                      "start": cluster_mention["start"] - sentence_start - 1,
                                      "end": cluster_mention["end"] - sentence_start - 1,
                                      "start_char": cluster_mention["start_char"] - sentence_start_char - 5,
                                      "end_char": cluster_mention["end_char"] - sentence_start_char - 5},
                             "to":   {"text": cluster["main"]["text"],
                                      "start": cluster["main"]["start"],
                                      "end": cluster["main"]["end"],
                                      "start_char": cluster["main"]["start_char"],
                                      "end_char": cluster["main"]["end_char"]},
                             # "cluster": cluster
                             }
                references.append(reference)
        return context, sentence, context_tokens, sentence_tokens, references


class POIGetCorefResource(GetCorefResource):
    general_expressions = [["this poi", "this thing"], []]
    typed_expressions = {
        "building": [["this building", "this construction", "construction"], []],
        "location": [["this location", "this place"], []]
    }

    def on_get(self, req, resp):
        intro = req.get_param("intro")
        poitype = req.get_param("poitype")
        context = req.get_param("context")
        sentence = req.get_param("sentence")
        self.response = {}
        context, sentence, context_tokens, sentence_tokens, refs = self.get_corefs(context, sentence, intro, poitype)
        self.response["context"] = context
        self.response["sentence"] = sentence
        self.response["context_tokens"] = context_tokens
        self.response["sentence_tokens"] = sentence_tokens
        self.response["references"] = refs
        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200

    def get_corefs(self, context, sentence, intro, poitype):
        _context = intro + " -- " + context
        context, sentence, context_tokens, sentence_tokens, refs = super(POIGetCorefResource, self).get_corefs(_context, sentence)
        applicable_expressions = [self.general_expressions[0] + [], self.general_expressions[1] + []]
        if poitype is not None:
            if poitype in self.typed_expressions:
                applicable_expressions[0] += self.typed_expressions[poitype][0]
                applicable_expressions[1] += self.typed_expressions[poitype][1]
            else:
                print("WARNING: poitype {} has no expressions".format(poitype))
        references = []
        for expr in applicable_expressions[0]:
            reference = None
            occurences = [m for m in re.finditer(expr, sentence)]
            if len(occurences) > 0:
                reference = {"from": {"text": occurences[0].group(0),
                             "start_char": occurences[0].start(),
                             "end_char": occurences[0].end()},
                             "to": "$POI"}
            if reference is not None:
                references.append(reference)
                break
        if len(references) > 0:     # manual overrides
            refs = references
        return context, sentence, context_tokens, sentence_tokens, refs


if __name__ == '__main__':
    port = int(sys.argv[1])
    size = str(sys.argv[2])
    clusters = ClusterResource(size)
    getcoref = GetCorefResource(clusters)
    poigetcoref = POIGetCorefResource(clusters)
    APP = falcon.API()
    APP.add_route('/clusters', clusters)
    APP.add_route('/getcoref', getcoref)
    APP.add_route('/poigetcoref', poigetcoref)
    HTTPD = make_server('0.0.0.0', port, APP)
    HTTPD.serve_forever()