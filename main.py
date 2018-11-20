#! /usr/bin/python

from subprocess import call
import hashlib
import json
import copy
import csv
import argparse
import itertools
import os
from pprint import pprint
from collections import namedtuple


class Nothing():
    def __init__(self, tag=None, pos=None):
        self.tag = tag
        self.pos = pos


tags = set()
maxpos = 0


class Node:
    def __init__(self, tag, pos=0, parent=Nothing(), data=None):
        self.tag = tag
        self.pos = pos
        self.data = data
        self.parent = parent
        self.children = []
        global tags, maxpos
        tags.add(tag)
        maxpos = max(pos, maxpos)

    def add_child(self, child):
        assert(child.parent == self)
        self.children.append(child)


def createDHT(parent, data):
    if type(data) is dict:
        for tag, val in data.items():
            if type(val) is list:
                id = 0
                for item in val:
                    new_node = Node(tag, id, parent)
                    parent.add_child(new_node)
                    createDHT(new_node, item)
                    id += 1
            elif type(val) is dict:
                new_node = Node(tag, 0, parent)
                parent.add_child(new_node)
                createDHT(new_node, val)
            else:
                new_node = Node(tag, 0, parent, val)
                parent.add_child(new_node)


def create_graph_viz_helper(root, file):
    for x in root.children:
        if len(x.children) == 0:
            file.write(str(x) + " [label=\"" + x.tag + "," + str(x.pos) + "," + str(x.data) + "\"];\n")
        else:
            file.write(str(x) + " [label=\"" + x.tag + "," + str(x.pos) + "\"];\n")
        file.write(str(root) + " -> " + str(x) + ";\n")
        create_graph_viz_helper(x, file)


def create_graph_viz(root, file_name):
    f = open(file_name, "w")
    f.write("digraph G {")
    f.write(str(root) + " [label=\"" + root.tag + "," + str(root.pos) + "\"];\n")
    create_graph_viz_helper(root, f)
    f.write("}")
    f.close()


def add_children_transitions(m):
    global tags
    stuff_to_add = []
    for tag in tags:
        for nodes, (old_data, old_path) in m.iteritems():
            new_nodes = set()
            new_data = set()
            for node in nodes:
                for x in node.children:
                    if x.tag == tag:
                        new_nodes.add(x)
                        if x.data is not None:
                            new_data.add(x.data)
            if len(new_nodes) != 0:
                new_path = copy.deepcopy(old_path)
                new_path.append("children," + tag)
                stuff_to_add.append((frozenset(new_nodes), new_data, new_path))
                # m[frozenset(new_nodes)] = (new_data, new_path)
        for (x, y, z) in stuff_to_add:
            m[x] = (y, z)


def add_pchildren_transitions(m):
    global tags, maxpos
    stuff_to_add = []
    for pos in range(0, maxpos+1):
        for tag in tags:
            for nodes, (old_data, old_path) in m.iteritems():
                new_nodes = set()
                new_data = set()
                for node in nodes:
                    for x in node.children:
                        if x.tag == tag and x.pos == pos:
                            new_nodes.add(x)
                            if x.data is not None:
                                new_data.add(x.data)
                if len(new_nodes) != 0:
                    new_path = copy.deepcopy(old_path)
                    new_path.append("pchildren," + tag + "," + str(pos))
                    stuff_to_add.append((frozenset(new_nodes), new_data, new_path))
                    # m[frozenset(new_nodes)] = (new_data, new_path)
    for (x, y, z) in stuff_to_add:
        m[x] = (y, z)


def dsl_function_string_helper(path):
    if len(path) == 0:
        return "s"
    current = path[0].split(',')
    if current[0] == "children":
        return "children(" + dsl_function_string_helper(path[1:]) + "," + current[1] + ")"
    if current[0] == "pchildren":
        return "pchildren(" + dsl_function_string_helper(path[1:]) + "," + current[1] + "," + current[2] + ")"


def dsl_function_string(path):
    return dsl_function_string_helper(list(reversed(path)))


def create_cartesian_product(l):
    result = []
    for element in itertools.product(*l):
        result.append(element)
    return result


def create_csv_file(column_names, table, file_name):
    f = open(file_name, "w")
    f.write(",".join(column_names) + "\n")
    for i in range(0, len(table)):
        for j in range(0, len(column_names)):
            f.write(str(table[i][j]))
            if j < len(column_names) - 1:
                f.write(",")
        f.write("\n")


def main():
    # Parsing arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-json", type=str, default='input.json', help="The path of the example json file input")
    parser.add_argument("-csv", type=str, default='table.csv', help="The path of the example CSV table file input")
    parser.add_argument("-gv", "--graphviz", type=str, help="The path of the generated graphviz file based on the"
                                                           " constructed Hierarchical Data Structure (HDS)")
    parser.add_argument("-s", "--showgraph", action="store_true", default=False,
                        help="A flag to show the produced GraphViz file")
    parser.add_argument("-q", "--quiet", action="store_true", default=False,
                        help="A flag to hide the DSL output")
    parser.add_argument("-o", type=str, help="The path of the overestimated table dump")
    args = parser.parse_args()

    # JSON - parsing input example
    json_data = open(args.json)
    data = json.load(json_data)
    json_data.close()

    # CSV - parsing output example
    column_names = []
    columns = []
    csv_file = open(args.csv)
    csv_data = csv.reader(csv_file)
    first = True
    for row in csv_data:
        if first:
            first = False
            column_names = row
            for i in range(0, len(column_names)):
                columns.append([])
        else:
            for i in range(0, len(row)):
                if row[i].isdigit():
                    row[i] = int(row[i])
                columns[i].append(row[i])
    
    root = Node(data.keys()[0])
    createDHT(root, data[data.keys()[0]])
    if args.graphviz is not None:
        create_graph_viz(root, args.graphviz)
        if args.showgraph:
            call(["dot", "-Tsvg", args.graphviz, "-o", "graph_tmp.svg"])
            call(["firefox", "graph_tmp.svg"])

    # create the finite deterministic state machine
    s = set()
    s.add(root)
    m = {frozenset(s): (set(), [])}

    k = -1
    while len(m) > k:
        k = len(m)
        add_children_transitions(m)
        add_pchildren_transitions(m)

    cartesian_material = []
    # print the results in the introduced DSL format
    i = 0
    for col in columns:
        i += 1
        k = 1
        for data, path in m.values():
            if set(col) <= data:
                if not args.quiet:
                    print "p" + str(i) + str(k) + " = " + dsl_function_string(path)
                if k == 1:
                    cartesian_material.append(data)
                k += 1

    table = create_cartesian_product(cartesian_material)
    # dump the overestimated csv
    if args.o is not None:
        create_csv_file(column_names, table, args.o)


if __name__ == "__main__":
    main()
