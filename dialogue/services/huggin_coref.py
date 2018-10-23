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
import os
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

        if self.nlp.pipeline[3][0].lower().strip() == "neuralcoref":
            self.nlp.pipeline[3][1].cfg["greedyness"] = float(os.getenv("GREEDYNESS", 0.5))
            self.nlp.pipeline[3][1].cfg["max_dist"] = float(os.getenv("MAX_DIST", 20))
            self.nlp.pipeline[3][1].cfg["max_dist_match"] = float(os.getenv("MAX_DIST_MATCH", 500))
            print("Parameters:\n" + json.dumps(self.nlp.pipeline[3][1].cfg, indent=4))

        print("Server loaded")
        self.response = None

    def mentions_overlap(self, main, mention):
        main_idxs = set(range(main["start_char"], main["end_char"]))
        mention_idxs = set(range(mention["start_char"], mention["end_char"]))
        return len(main_idxs & mention_idxs) > 0

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
                    _main = get_dict_of_span(main)
                    _cluster["main"] = _main
                    _cluster["mentions"] = []
                    for mention in cluster.mentions:
                        _mention = get_dict_of_span(mention)
                        if not self.mentions_overlap(_main, _mention):
                            _cluster["mentions"].append(_mention)
                    if len(_cluster["mentions"]) > 0:
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
    DELIM = " ---. "

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
        # self.response["context_tokens"] = context_tokens
        # self.response["sentence_tokens"] = sentence_tokens
        self.response["references"] = refs
        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200

    def resolve_text(self, text, refs):
        if len(refs) == 0:
            return None
        replacements = []
        for ref in refs:
            s, e = ref["from"]["start_char"], ref["from"]["end_char"]
            to = ref["to"]["text"]
            replacements.append((s, e, to))
        replacements = sorted(replacements, key=lambda x: x[0], reverse=True)
        prev_e = 0
        acc = []
        for replacement in replacements:
            s, e, to = replacement
            if s < prev_e:
                print("WARNING: overlapping replacements: replace from {} to {} by {} in {}".format(s, e, to, text))
                continue        # ignore
            acc.append(text[prev_e:s])
            acc.append(to)
            prev_e = e
        acc.append(text[prev_e:])
        acc = "".join(acc)
        return acc

    def get_corefs(self, context, sentence):
        text = context + self.DELIM + sentence
        clusters = self.clusterer.get_clusters(text)

        sentence_start_char = text.find(self.DELIM)

        context = text[:sentence_start_char]
        sentence = text[sentence_start_char+len(self.DELIM):]
        references = []
        if "clusters" in clusters:
            for cluster in clusters["clusters"]:
                cluster_mention = None
                for mention in cluster["mentions"]:
                    if mention["start_char"] >= sentence_start_char:
                        cluster_mention = mention
                        break
                if cluster_mention is not None:
                    # mentioned in sentence !
                    reference = {"from": {"text": cluster_mention["text"],
                                          # "start": cluster_mention["start"] - sentence_start - 1,
                                          # "end": cluster_mention["end"] - sentence_start - 1,
                                          "start_char": cluster_mention["start_char"] - sentence_start_char - len(self.DELIM),
                                          "end_char": cluster_mention["end_char"] - sentence_start_char - len(self.DELIM)},
                                 "to":   {"text": cluster["main"]["text"],
                                          # "start": cluster["main"]["start"],
                                          # "end": cluster["main"]["end"],
                                          "start_char": cluster["main"]["start_char"],
                                          "end_char": cluster["main"]["end_char"]},
                                 # "cluster": cluster
                                 }
                    references.append(reference)

        # resolved
        resolved_sentence = self.resolve_text(sentence, references)
        if resolved_sentence is None:
            resolved_sentence = sentence

        return context, sentence, references, resolved_sentence


class POIGetCorefResource(GetCorefResource):
    """
    HOW THIS WORKS
    - uses neural-coref for coreference resolution (see GetCorefResource). Returns result in span-return format.
    - supports manual $POI-referring expressions, which can be typed.
        If manual expression matches, results of neural-coref are discarded.
        Only first occurrence of first matched manual expression is used.
        Returns result in $POI-return format
    - for neural-coref, transforms span-return to $POI-return if intro and poispan in intro (char-level spec) is provided

    Example usage:
        http://localhost:6007/poigetcoref?poitype=building&poispan=20-37&intro=we%20currently%20are%20at%20the%20tower%20of%20pisa&context=mr.%20paul%20likes%20dumplings.%20he%20loves%20them.%20&sentence=who%20built%20this%20tower

    GET arguments:
    - context:      string with dialogue history
    - sentence:     current sentence to resolve referring expressions of.
                    All other clusters in context that do not involve "sentence" are not returned.
    - intro:        (optional) string introducing $POI. Can be simple sentence: e.g. "We are at the tower of Pisa"
                    See also poitype and poispan for optional additional functionality.
    - poitype:      (optional) type of poi. If not specified, typed_expressions is not used
    - poispan:      (optional) expects span in format "b-e" where "b" and "e" are two integers.
                    If not specified, $POI resolution from neural-coref results is not done.
                    neural-coref $POI resolution currently requires the coref span to match at least half of the poispan
    """
    general_expressions = [["this poi", "this thing", "this place"], ["this", "it"]]
    #   [[strong expressions], [weak expressions]]
    #       - strong expressions replace neural-coref results,
    #       - weak expressions only invoked when neither strong expressions or neural-coref yielded any results
    typed_expressions = {
        "building": [["this building", "this construction", "construction"], []],
        "location": [["this location", "this place"], []]
    }

    def on_get(self, req, resp):
        intro = req.get_param("intro")
        poitype = req.get_param("poitype")
        poispan = req.get_param("poispan")
        if poispan is not None:
            poispan = [int(x) for x in poispan.split("-")]
        context = req.get_param("context")
        sentence = req.get_param("sentence")
        self.response = {}
        context, sentence, refs, resolved_sentence = self.get_corefs(context, sentence, intro, poitype, poispan)
        self.response["context"] = context
        self.response["sentence"] = sentence
        # self.response["context_tokens"] = context_tokens
        # self.response["sentence_tokens"] = sentence_tokens
        self.response["references"] = refs
        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200

    def do_poi_expressions(self, sentence, poitype=None, which="strong"):
        applicable_expressions = [self.general_expressions[0] + [], self.general_expressions[1] + []]
        if poitype is not None:
            if poitype in self.typed_expressions:
                applicable_expressions[0] += self.typed_expressions[poitype][0]
                applicable_expressions[1] += self.typed_expressions[poitype][1]
            else:
                print("WARNING: poitype {} has no expressions".format(poitype))
        references = []
        which = 0 if which == "strong" else 1
        for expr in applicable_expressions[which]:
            expr = "(?:^|(?<=\s|\?|\.|!)){}(?=\s|\?|\.|!|$)".format(expr)      # DONE: better fix, taking into account other kind of punctuation
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
        resolved_sentence = sentence
        assert(len(references) < 2)
        if len(references) > 0:
            ref = references[0]
            resolved_sentence = sentence[:ref["from"]["start_char"]] + "$POI" + sentence[ref["from"]["end_char"]:]
        return references, resolved_sentence

    def get_corefs_(self, context, sentence):
        return super(POIGetCorefResource, self).get_corefs(context, sentence)

    def get_corefs(self, context, sentence, intro, poitype, poispan):
        _context = intro + " -- " + context

        refs, resolved_sentence = self.do_poi_expressions(sentence, poitype=poitype, which="strong")

        if len(refs) == 0:
            context, sentence, refs, resolved_sentence = self.get_corefs_(_context, sentence)
            if poispan is None or intro is None:
                pass
            else:
                for ref in refs:        # neuralcoref refs
                    if ref["to"]["start_char"] >= poispan[0] and ref["to"]["end_char"] <= poispan[1]:
                        poispanlen = poispan[1] - poispan[0]
                        refspanlen = ref["to"]["end_char"] - ref["to"]["start_char"]
                        if refspanlen / poispanlen > 0.5:
                            ref["to"] = "$POI"

        if len(refs) == 0:       # previous steps didn't return anything --> use weak manual expressions
            refs, resolved_sentence = self.do_poi_expressions(sentence, poitype=poitype, which="weak")
        return context, sentence, refs, resolved_sentence


class EntityGetCorefResource(POIGetCorefResource):
    def on_get(self, req, resp):
        print("request came in ...")
        data = req.get_param("data")
        print("request data: {}".format(data))
        data = json.loads(data)
        context = data["context"]
        entities = data["entities"]
        sentence = data["sentence"]
        self.response = {}
        context, sentence, refs, resolved_sentence = self.get_corefs(context, sentence, entities)
        self.response["context"] = context
        self.response["sentence"] = sentence
        # self.response["context_tokens"] = context_tokens
        # self.response["sentence_tokens"] = sentence_tokens
        self.response["references"] = refs
        self.response["resolved_sentence"] = resolved_sentence
        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200

    def get_corefs(self, context, sentence, entities):
        assert("$POI" in entities)

        print(context, sentence, entities)

        # STRONG POI EXPRESSIONS
        poitype = None
        if "$POI" in entities and "type" in entities["$POI"]:
            poitype = entities["$POI"]["type"]

        refs, resolved_sentence = self.do_poi_expressions(sentence, poitype=poitype, which="strong")

        # RESOLVING ENTITIES
        if len(refs) == 0:     # no strong expressions
            # do neural-coref for sentence
            context, sentence, refs, resolved_sentence = self.get_corefs_(context, sentence)
            #  check if we can resolve neuralcoref refs to entities --> replace
            for entity in entities:
                entity_span = None
                if "span" in entities[entity]:
                    entity_span = entities[entity]["span"]
                if entity_span is None:
                    pass
                else:
                    for ref in refs:        # neuralcoref refs
                        if isinstance(ref["to"], dict) and ref["to"]["start_char"] >= entity_span[0] and ref["to"]["end_char"] <= entity_span[1]:
                            entity_spanlen = entity_span[1] - entity_span[0]
                            refspanlen = ref["to"]["end_char"] - ref["to"]["start_char"]
                            if refspanlen / entity_spanlen > 0.5:
                                ref["to"] = entity

        # WEAK POI EXPRESSIONS
        if len(refs) == 0:       # previous steps didn't return anything --> use weak manual expressions
            refs, resolved_sentence = self.do_poi_expressions(sentence, poitype=poitype, which="weak")
        return context, sentence, refs, resolved_sentence


class TestJsonResource(object):
    def on_get(self, req, resp):
        data_json = req.get_param("data")
        data = json.loads(data_json)
        print(data)


def test_shelve():
    import shelve
    with shelve.open("/tmp/shelvetest") as s:
        s["id"] = {
            "a": list(),
            "b": "0"
        }
    with shelve.open('/tmp/shelvetest', writeback=True) as s:
        s["id"]["a"].append("qsdfqsdf")

    with shelve.open("/tmp/shelvetest") as s:
        print(s["id"])


if __name__ == '__main__':
    test_shelve()
    print(sys.argv)
    try:
        port = int(sys.argv[1])
        size = str(sys.argv[2])
    except Exception as e:
        print("getting args failed, using defaults")
        port = 8008
        size = "medium"
    APP = falcon.API()
    clusters = ClusterResource(size)
    getcoref = GetCorefResource(clusters)
    poigetcoref = POIGetCorefResource(clusters)
    APP.add_route('/clusters', clusters)
    APP.add_route('/getcoref', getcoref)
    APP.add_route('/poigetcoref', poigetcoref)
    APP.add_route('/entitygetcoref', EntityGetCorefResource(clusters))
    APP.add_route('/testjson', TestJsonResource())
    HTTPD = make_server('0.0.0.0', port, APP)
    HTTPD.serve_forever()
