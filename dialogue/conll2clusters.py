import re
import json
from tabulate import tabulate
from pprint import PrettyPrinter
import requests as req


def conll2clusters(inp, out):
    pp = PrettyPrinter()
    lines = out.strip().split("\n")
    clusters = {}
    tokens = []
    resolved = ""
    tok_nr = 0
    for line in lines:
        line = line.strip().split("\t")
        if len(line) > 1:
            token = line[1]
            coref_info = line[9]
            print(coref_info, token, line)
            tokens.append(token)
            if coref_info != "-":
                cluster_ids = coref_info.split("|")
                for cluster_id in cluster_ids:
                    openm = re.match("^\((\d+)$", cluster_id)
                    closem = re.match("^(\d+)\)$", cluster_id)
                    singlem = re.match("^\((\d+)\)$", cluster_id)
                    if openm:
                        # start of a cluster
                        cid = int(openm.group(1))
                        if cid not in clusters:
                            clusters[cid] = []
                        clusters[cid].append([tok_nr, None])
                    elif closem:
                        cid = int(closem.group(1))
                        assert(cid in clusters)
                        clusters[cid][-1][1] = tok_nr+1
                    elif singlem:
                        cid = int(singlem.group(1))
                        if cid not in clusters:
                            clusters[cid] = []
                        clusters[cid].append([tok_nr, tok_nr+1])


            tok_nr += 1
    pp.pprint(tokens)
    pp.pprint(clusters)

    tok2char = tokpos2charpos(inp, tokens)
    pp.pprint(tok2char)

    outclusters = []
    for k, v in clusters.items():
        # print(v)
        outcluster = {"main": {}, "mentions": []}
        tokstart = v[0][0]
        tokend = v[0][1]
        toktext = " ".join(tokens[tokstart:tokend])
        chrstart = tok2char[tokstart][0]
        chrend = tok2char[tokend-1][1]
        chrtext = inp[chrstart:chrend]
        assert(toktext.replace(" ", "") == chrtext.replace(" ", ""))
        outcluster["main"] = {"start": tokstart,
                              "end":   tokend,
                              "start_char": chrstart,
                              "end_char": chrend,
                              "text":  chrtext}
        del v[0]
        for ve in v:
            # print(v)
            tokstart = ve[0]
            tokend = ve[1]
            toktext = " ".join(tokens[tokstart:tokend])
            chrstart = tok2char[tokstart][0]
            chrend = tok2char[tokend-1][1]
            chrtext = inp[chrstart:chrend]
            assert(toktext.replace(" ", "") == chrtext.replace(" ", ""))
            mention = {"start": tokstart,
                       "end":   tokend,
                       "start_char": chrstart,
                       "end_char": chrend,
                       "text":  chrtext}
            outcluster["mentions"].append(mention)
        outclusters.append(outcluster)
    pp.pprint(outclusters)
    return outclusters, tokens


def tokpos2charpos(text, tokens):
    if text.replace(" ", "") != " ".join(tokens).replace(" ", ""):
        print(text)
        print(tokens)
        raise Exception("sum ting wong: {}, {}".format(str(text), str(tokens)))
    text_ = text + ""
    tokpos2charpos = {}
    acc = 0
    for i, token in enumerate(tokens):
        startchar = text_.find(token)
        endchar = startchar + len(token)
        assert(len(text_[:startchar].replace(" ", "")) == 0)
        tokpos2charpos[i] = (acc + startchar, acc + endchar)
        text_ = text_[endchar:]
        acc += endchar
    return tokpos2charpos



if __name__ == '__main__':
    p = "sampleout.conll"
    inp = "Mein Schwester hat einen  Hund. Sie liebt ihn . Aber nicht mich."
    with open(p, "r") as f:
        out = f.read()
        clusters, tokens = conll2clusters(inp, out)