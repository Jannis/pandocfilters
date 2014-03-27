#!/usr/bin/env python
# -
# Copyright (C) 2014 Jannis Pohlmann <jannis.pohlmann@codethink.co.uk>
# License: BSD3


import cliapp
import hashlib
import os
import re

from pandocfilters import toJSONFilter, Image, Para, Str


class EndUMLMissingError(Exception):

    def __init__(self, code):
        self.code = code

    def __str__(self):
        return '@enduml missing at the end of a PlantUML code block: %s' % \
            self.code


class NestedUMLError(Exception):

    def __init__(self, code):
        self.code = code

    def __str__(self):
        return 'Nested UML blocks are unsupported: %s' % self.code


class PlantUMLFilter(cliapp.Application):

    def add_settings(self):
        self.settings.string(['embed-format', 'e'],
                             'Format images are embedded as (e.g. png, pdf)',
                             metavar='png|pdf',
                             default=None)
        self.settings.string(['format', 'f'],
                             'Output format of PlantUML images (png/eps/svg)',
                             metavar='png|eps|svg',
                             default=None)
        self.settings.string(['out-dir', 'o'],
                             'Directory where the documentation is created',
                             metavar='DIR',
                             default=None)
        self.settings.string(['image-dir', 'i'],
                             'Directory for PlantUML images',
                             metavar='DIR',
                             default=None)

    def extract_uml_blocks(self, lines):
        blocks = []
        in_block = False
        for line in lines:
            if line.startswith('@startuml'):
                if not in_block:
                    in_block = True
                    blocks.append([])
                else:
                    raise NestedUMLError('\n'.join(lines))
            elif line.startswith('@enduml'):
                blocks[-1].append(line)
                in_block = False
            if in_block:
                blocks[-1].append(line)
        return blocks

    def generate_uml(self, uml):
        image_data = self.runcmd(['java', '-jar',
                                  os.path.join(os.path.dirname(__file__),
                                               'plantuml.jar'),
                                  '-t%s' % self.settings['format'],
                                  '-p'], feed_stdin=uml)
        sha1 = hashlib.sha1(uml).hexdigest()
        filename = os.path.join(self.settings['image-dir'],
                                '%s.%s' % (sha1, self.settings['format']))
        with open(filename, 'wb+') as f:
            f.write(image_data)
        return filename

    def convert_image(self, source, destination):
        conversion = (self.settings['format'], self.settings['embed-format'])
        if conversion == ('svg', 'pdf'):
            self.runcmd(['rsvg-convert', '-f', 'pdf',
                         '-o', destination, source])
        elif conversion == ('eps', 'pdf'):
            self.runcmd(['epstopdf', '--outfile=%s' % destination, source])

    def process_uml(self, lines):
        if lines[0].startswith('@startuml:') \
                or lines[0] == '@startuml':
            parts = lines[0].split(':', 1)
            title = parts[1] if len(parts) > 1 else None
            if not lines[-1] == '@enduml':
                raise EndUMLMissingError('\n'.join(lines))
            else:
                uml = '\n'.join(lines[1:-1])
                filename = self.generate_uml(uml)
                embed_filename = re.sub(
                    r'%s$' % self.settings['format'],
                    self.settings['embed-format'],
                    filename)

                self.convert_image(filename, embed_filename)

                relative_filename = os.path.relpath(
                    embed_filename, self.settings['out-dir'])

                if title:
                    return Para([Image([Str(title.strip())],
                                       [relative_filename, 'fig:'])])
                else:
                    return Para([Image([], [relative_filename, 'fig:'])])

    def plantuml(self, key, value, format, meta):
        if key == 'CodeBlock':
            [[ident, classes, keyvalues], code] = value
            lines = code.splitlines()
            if not lines:
                return None
            else:
                uml_blocks = self.extract_uml_blocks(lines)
                paragraphs = []
                for block in uml_blocks:
                    paragraphs.append(self.process_uml(block))
                return paragraphs
        return None

    def process_args(self, args):
        if not self.settings['out-dir']:
            raise Exception('No --out-dir specified')
        if not self.settings['image-dir']:
            raise Exception('No --image-dir specified')
        if not self.settings['format']:
            raise Exception('No --format specified')
        if not self.settings['embed-format']:
            raise Exception('No --embed-format specified')

        toJSONFilter(self.plantuml)


if __name__ == '__main__':
    PlantUMLFilter().run()
