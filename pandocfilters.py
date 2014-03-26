# Author: John MacFarlane <jgm@berkeley.edu>
# Copyright: (C) 2013 John MacFarlane <jgm@berkeley.edu>
# Copyright: (C) 2014 Jannis Pohlmann <jannis.pohlmann@codethink.co.uk>
# License: BSD3


"""Python functions for processing the pandoc AST serialized as JSON."""


import sys
import json


def walk(x, action, format, meta):
    """Apply an action to every object in a tree and return the result."""
    if isinstance(x, list):
        array = []
        for item in x:
            if isinstance(item, dict):
                res = action(item.keys()[0], item.values()[0], format, meta)
                if res is None:
                    array.append(walk(item, action, format, meta))
                elif isinstance(res, list):
                    for z in res:
                        array.append(walk(z, action, format, meta))
                else:
                    array.append(walk(res, action, format, meta))
            else:
                array.append(walk(item, action, format, meta))
        return array
    elif isinstance(x, dict):
        obj = {}
        for k in x:
            obj[k] = walk(x[k], action, format, meta)
        return obj
    else:
        return x


def toJSONFilter(action):
    """Convert an action into a Pandoc JSON filter.

    The resulting filter reads a JSON-formatted pandoc document from stdin,
    transforms it by walking the tree with the action, and returns a new
    JSON-formatted pandoc document to stdout.

    The argument is a function action(key, value, format, meta), where key is
    the type of the pandoc object (e.g. 'Str', 'Para'), value is the contents
    of the object (e.g. a string for 'Str', a list of inline elements for
    'Para'), format is the target output format (which will be taken for the
    first command line argument if present), and meta is the document's
    metadata.

    If the function returns None, the object to which it applies will remain
    unchanged. If it returns an object, the object will be replaced. If
    it returns a list, the list will be spliced in to the list to which the
    target object belongs. (So, an empty list deletes the object.)

    """

    doc = json.loads(sys.stdin.read())
    if len(sys.argv) > 1:
        format = sys.argv[1]
    else:
        format = ""
    altered = walk(doc, action, format, doc[0].get('unMeta', None))
    json.dump(altered, sys.stdout)


def stringify(x):
    """Concatenate all strings in a tree and return the result.

    This drops all formatting in the tree.

    """
    result = []

    def go(key, val, format, meta):
        if key == 'Str':
            result.append(val)
        elif key == 'Code':
            result.append(val[1])
        elif key == 'Math':
            result.append(val[1])
        elif key == 'LineBreak':
            result.append(" ")
        elif key == 'Space':
            result.append(" ")

    walk(x, go, "", {})
    return ''.join(result)


def attributes(attrs):
    """Return an attribute list constructed from the dictionary attrs."""
    attrs = attrs or {}
    ident = attrs.get("id", "")
    classes = attrs.get("classes", [])
    keyvals = [[x, attrs[x]]
               for x in attrs
               if (x != "classes" and x != "id")]
    return [ident, classes, keyvals]


def elt(eltType, numargs):
    """Return a constructor function for a typed Pandoc JSON element."""
    def fun(*args):
        if len(args) != numargs:
            raise Exception('%s expects %i arguments but was given %i' %
                            (eltType, numargs, len(args)))
        if len(args) == 1:
            xs = args[0]
        else:
            xs = args
        return {eltType: xs}
    return fun


# Constructors for block elements

Plain = elt('Plain', 1)
Para = elt('Para', 1)
CodeBlock = elt('CodeBlock', 2)
RawBlock = elt('RawBlock', 2)
BlockQuote = elt('BlockQuote', 1)
OrderedList = elt('OrderedList', 2)
BulletList = elt('BulletList', 1)
DefinitionList = elt('DefinitionList', 1)
Header = elt('Header', 3)
HorizontalRule = elt('HorizontalRule', 0)
Table = elt('Table', 5)
Div = elt('Div', 2)
Null = elt('Null', 0)


# Constructors for inline elements

Str = elt('Str', 1)
Emph = elt('Emph', 1)
Strong = elt('Strong', 1)
Strikeout = elt('Strikeout', 1)
Superscript = elt('Superscript', 1)
Subscript = elt('Subscript', 1)
SmallCaps = elt('SmallCaps', 1)
Quoted = elt('Quoted', 2)
Cite = elt('Cite', 2)
Code = elt('Code', 2)
Space = elt('Space', 0)
LineBreak = elt('LineBreak', 0)
Math = elt('Math', 2)
RawInline = elt('RawInline', 2)
Link = elt('Link', 2)
Image = elt('Image', 2)
Note = elt('Note', 1)
Span = elt('Span', 2)
