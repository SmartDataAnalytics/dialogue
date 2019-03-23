import re
import requests
import tabulate
import json
import sys


SYSTEM = "SYSTEM"
USER = "USER"


def get_out(context, sentence):
    i = 0
    history = ""
    entities = {}
    for context_sentence in context:
        for a, b in context_sentence[1]:
            entid = "$ENT{}".format(len(entities)+1)
            entities[entid] = {"span": [a+len(history), b+len(history)]}
        history += context_sentence[0] + "\n"
    return history, entities, sentence


def run(port=8008, lang="en", skipcoref=False):
    greeting = ("Hello, my name is Tony!", [])
    context = [greeting]
    stop = False
    turn = SYSTEM

    print("{}: {}".format(turn, greeting[0]))
    turn = USER

    while not stop:
        # print("{}: {}".format(turn, context[-1]))
        x = input("{}: ".format(turn))
        if x in "%stop %quit %exit".split():
            print()
            print("Collected conversation: --------------------")
            c, e, s = get_out(context, "")
            print(tabulate.tabulate([list(c), list(range(len(c)))]))
            print(e)
            stop = True
        # TODO process x here
        # extract new entities
        x_ = ""
        entopen = False
        j = 0
        newent_start = None
        newents = []
        for i in range(len(x)):
            if x[i] == "%":
                if entopen:
                    newents.append((newent_start, j))
                    entopen = False
                else:
                    entopen = True
                    newent_start = j
            else:
                x_ += x[i]
                j += 1
        print(x_)
        newents_ = [(x_[a: b], a, b) for a, b in newents]
        if len(newents_) > 0:
            print("New entities: {}".format(str(newents_)))
        # check coref
        c, e, s = get_out(context, x_)
        if not skipcoref:
            data = {
                "context": c,
                "sentence": s,
                "entities": e
            }
            data_json = json.dumps(data)
            print(data_json)
            payload = {"data": data_json}
            r = requests.get("http://localhost:{}/{}/entitygetcoref".format(port, lang),
                             params=payload)
            print(r.text)
        # update state for next iter
        context.append((x_, newents))
        turn = SYSTEM if turn == USER else USER


if __name__ == '__main__':
    port = int(sys.argv[1])
    lang = str(sys.argv[2])
    run(port, lang)