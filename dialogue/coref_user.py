## !!!! USE NOTEBOOK INSTEAD (in dialogue/notebooks !!!
import re
import json
import requests
import numpy as np
import sys


def run(port=6007, lang="en"):
    if lang == "de":
        context = """ Wir sind am schiefen Turm von Pisa. Wer hat es gebaut? Giuseppe Napolitano baute diesen Turm. """
        sentence = "Wann wurde es gebaut?"
        sentence = "Wann wurde er geboren?"
        sentence = "Was ist dies POI?"
        poi_start = context.find("schiefen Turm von Pisa")
        poi_end = poi_start + len("schiefen Turm von Pisa")
        builder_start = context.find("Giuseppe Napolitano")
        builder_end = builder_start + len("Giuseppe Napolitano")
    elif lang == "en":
        context = """ We are at the leaning tower of Pisa. Who built it? Giuseppe Napolitano built this tower. """
        sentence = "When was it built?"
        poi_start = context.find("the leaning tower of Pisa")
        poi_end = poi_start + len("the leaning tower of Pisa")
        builder_start = context.find("Giuseppe Napolitano")
        builder_end = builder_start + len("Giuseppe Napolitano")
    else:
        raise Exception("unknown language '{}'".format(lang))

    entities = {
        "$POI": {"span": [poi_start, poi_end], "type": "building"},
        "$BUILDER": {"span": [builder_start, builder_end]}
    }


    data = {"context": context,
            "entities": entities,
            "sentence": sentence}
    data_json = json.dumps(data)

    payload = {"data": data_json}
    r = requests.get("http://localhost:{}/{}/entitygetcoref".format(port, lang), params=payload)
    print(r.text)


def uri2label(uri):
    urire = re.compile("http://dbpedia\.org/resource/(.+)")
    label = urire.match(uri).group(1).replace("_", " ")
    return label


def get_links(p="../dial2_purenl.json", ppoi="../hit2poi250.json"):
    d = json.load(open(p))
    poi = json.load(open(ppoi))
    poi = {k: v["entities"] for k, v in poi.items()}
    di = list(d.items())
    print(len(poi))
    print(len(d))
    print(set(poi.keys()) - set(d.keys()))

    #print(di[0])
    #print(poi)
    for k, v in poi.items():
        label = uri2label(v)
        # print(k, label)

    # print(d["3QXFBUZ4ZKO2ZRDNVK0EHHDTV1MGUQ"])
    # return

    ret = {}
    for k in d:
        print(k)
        dialog = d[k]
        dialog_poi = poi[k]
        links = get_links_one(dialog, dialog_poi)
        ret[k] = links

    k = di[2][0]
    print(d[k])
    print(ret[k])

    return ret


def get_links_one(dialog, poi):
    prefix = "This is "
    intro = prefix + uri2label(poi)
    poistart = len(prefix)
    poiend = poistart + len(uri2label(poi))
    # print(intro)

    entities = {
        "$POI": {"span": [poistart, poiend]},
    }

    lines = [intro] + dialog
    lineseps = [0] + list(np.cumsum([len(x)+1 for x in lines]))

    links = []

    # print(lineseps)
    links = {}
    for i in range(1, len(lines), 2):
        context = "\n".join(lines[:i])
        sentence = lines[i]
        # print(context)
        # print("Sentence: " + sentence)

        data = {"context": context,
                "entities": entities,
                "sentence": sentence}
        data_json = json.dumps(data)

        payload = {"data": data_json}
        r = requests.get("http://localhost:8008/entitygetcoref", params=payload)
        # print("")
        # print(json.loads(r.text)["references"])
        # print(json.loads(r.text))
        whichline = None
        for ref in json.loads(r.text)["references"]:
            # print("refers to: " + str(ref["to"]))
            # find where in context the ref falls based on lineseps
            for j in range(len(lineseps[:-1])):
                l_start, l_end = lineseps[j], lineseps[j+1]
                if ref["to"] == "$POI":
                    whichline = 0
                    break
                if l_start <= ref["to"]["start_char"] and l_end >= ref["to"]["end_char"]:
                    whichline = j
                    break # found
            # print(whichline)
        if whichline is not None:
            links[i-1] = [whichline-1]
    return links


if __name__ == '__main__':
    port = int(sys.argv[1])
    lang = sys.argv[2]
    run(port=port, lang=lang)
    # ret = get_links()
    # json.dump(ret, open("dial2_predlinks.json", "w"))

