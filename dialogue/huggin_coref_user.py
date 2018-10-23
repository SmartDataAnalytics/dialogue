## !!!! USE NOTEBOOK INSTEAD (in dialogue/notebooks !!!
import re
import json
import requests


def run():
    context = """ We are at the leaning tower of Pisa. Who built it? Giuseppe Napolitano built this tower. When was it built? In the nineteenth century. """
    poi_start = context.find("the leaning tower of Pisa")
    poi_end = poi_start + len("the leaning tower of Pisa")
    builder_start = context.find("Giuseppe Napolitano")
    builder_end = builder_start + len("Giuseppe Napolitano")

    entities = {
        "$POI": {"span": [poi_start, poi_end], "type": "building"},
        "$BUILDER": {"span": [builder_start, builder_end]}
    }

    sentence = "When was it built?"

    data = {"context": context,
            "entities": entities,
            "sentence": sentence}
    data_json = json.dumps(data)

    payload = {"data": data_json}
    r = requests.get("http://localhost:6007/entitygetcoref", params=payload)
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


    get_links_onedialog(di[1][1], poi[di[1][0]])


def get_links_onedialog(dialog, poi):
    # print("getting links from coref for dialog about {} \n {}".format(poi, dialog))
    prefix = "This is "
    intro = prefix + uri2label(poi)
    poistart = len(prefix)
    poiend = poistart + len(uri2label(poi))
    print(intro)

    entities = {
        "$POI": {"span": [poistart, poiend]},
    }

    context = "\n".join(dialog[:-2])
    sentence = dialog[-2]

    data = {"context": context,
            "entities": entities,
            "sentence": sentence}
    data_json = json.dumps(data)

    payload = {"data": data_json}
    r = requests.get("http://localhost:8008/entitygetcoref", params=payload)
    print("")
    print(r.text)


if __name__ == '__main__':
    get_links()

