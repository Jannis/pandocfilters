#!/usr/bin/env python
# -
# Copyright (C) 2014 Jannis Pohlmann <jannis.pohlmann@codethink.co.uk>
# License: BSD3

import cliapp
import json
import os

from pandocfilters import toJSONFilter


def stringify_include(para):
    return ' '.join([x['Str']
                     for x in para if isinstance(x, dict)
                     if 'Str' in x])


class IncludeDocumentMissingError(Exception):

    def __init__(self, para):
        self.para = para

    def __str__(self):
        return 'Include specifies no document to include: %s' % \
            stringify_include(self.para)


class IncludeQuotesMissingError(Exception):

    def __init__(self, para):
        self.para = para

    def __str__(self):
        return 'Include lacks quotes around the document: %s' % \
            stringify_include(self.para)


class IncludeInvalidArgumentError(Exception):

    def __init__(self, para):
        self.para = para

    def __str__(self):
        return 'Include has an invalid argument ' \
               '(expected "<document>"): %s' % self.para


class IncludeFailedError(Exception):

    def __init__(self, filename, error):
        self.filename = filename
        self.error = error

    def __str__(self):
        return 'Include of "%s" failed: %s' % (self.filename, self.error)


class IncludeFilter(cliapp.Application):

    def __init__(self):
        cliapp.Application.__init__(self)

    def add_settings(self):
        self.settings.string(['directory', 'd'],
                             'Base directory where source files are located',
                             metavar='DIR',
                             default=None)

    def extract_include(self, para):
        if isinstance(para, list) and para:
            no_spaces = [x for x in para if not x == u'Space']

            is_include1 = no_spaces[0] == {u'Str': u'%include'}
            is_include2 = len(no_spaces) >= 2 and \
                no_spaces[0] == {u'Str': u'%'} and \
                no_spaces[1] == {u'Str': u'include'}

            document = None
            if is_include1:
                if len(no_spaces) < 2:
                    raise IncludeDocumentMissingError(para)
                elif not isinstance(no_spaces[1], dict) or \
                        'Str' not in no_spaces[1]:
                    raise IncludeInvalidArgumentError(para)
                else:
                    document = no_spaces[1]['Str']
            elif is_include2:
                if len(no_spaces) < 3:
                    raise IncludeDocumentMissingError(para)
                elif not isinstance(no_spaces[2], dict) or \
                        'Str' not in no_spaces[2]:
                    raise IncludeInvalidArgumentError(para)
                else:
                    document = no_spaces[2]['Str']

            if document:
                if not document.startswith('"') or \
                        not document.endswith('"'):
                    raise IncludeQuotesMissingError(para)
                else:
                    return document[1:-1]
            else:
                return None

    def include(self, key, value, format, meta):
        if key == 'Para':
            document = self.extract_include(value)
            if document:
                filename = os.path.join(self.settings['directory'],
                                        '%s.mdwn' % document)
                try:
                    output = self.runcmd(['pandoc', '-s', '-tjson', filename])
                    data = json.loads(output)
                    return data[1]
                except Exception, e:
                    print e
                    raise IncludeFailedError(filename, e)
        return None

    def process_args(self, args):
        toJSONFilter(self.include)


if __name__ == '__main__':
    IncludeFilter().run()
