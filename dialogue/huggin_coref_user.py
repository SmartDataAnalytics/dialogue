## !!!! USE NOTEBOOK INSTEAD (in dialogue/notebooks !!!

import json
import requests

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

