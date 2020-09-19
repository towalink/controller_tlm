#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import jinja2
import logging
import os


logger = logging.getLogger(__name__)


class JinjaTransformer(object):
    """Class for evaluating Jinga2 template files and saving the result"""

    def __init__(self, templatedir='/', globalvars=None):
        '''Object initialization'''
        self.templatedir = templatedir
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.templatedir))
        if globalvars is not None:
            self.env.globals.update(globalvars)
    
    def load_template(self, filename):
        '''Loads a Jinja2 template from the given file'''
        self._filename = filename
        self.template = self.env.get_template(self._filename)

    def render_template(self, data):
        '''Renders the template with the given data (dictionary)'''
        if self.template is None:
            return
        try:
            self.output = self.template.render(**data)
        except Exception as e:
            logger.error(f'Error rendering template file [{self._filename}]:\n' + str(e))
            raise

    def save_output(self, filename):
        '''Saves the rendered output to the given file'''
        filename = os.path.join(self.templatedir, filename)
        try:
            with open(filename, 'w') as outputfile:
                outputfile.write(self.output)
        except OSError as e:
            logger.error('Could not write file [{0}], [{1}]'.format(filename, str(e)))
            raise

    def render_template_to_file(self, template, outfile, data=None):
        '''Renders the given template string to the specified output file using the provided data (dictionary)'''
        self.template = jinja2.Template(template)
        self.render_template(data)
        self.save_output(outfile)

    def render_templatefile_to_file(self, infile, outfile=None, data=None):
        '''Convenience function to render the given template to the specified output using the provided data (dictionary)'''
        if outfile is None:
            if infile.endswith('.jinja'):
                outfile = infile[0:-6]
            else:
                raise ValueError('No output filename specified')
        self.load_template(infile)
        self.render_template(data)
        self.save_output(outfile)

    def render_templatefiles_to_files(self, dir, data=None, filter_ignore=None):
        '''Convenience function to render all template files in the given directory using the provided data (dictionary)'''
        if filter_ignore is None:
            filter_ignore = []
        files = [ item for item in os.listdir(dir) if item.endswith('.jinja') and not (item in filter_ignore) ]
        for file in files:
            self.render_templatefile_to_file(file, data=data)


def clever_function(a, b):
    return u''.join([b, a])

if __name__ == '__main__':
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('/mnt/hdd1/dirk/AnnikaDirk/Versionsverwaltung/towalink/ctrl/src'))
    tl = { 'clever_function': clever_function }
    env.globals['tl'] = tl
    person = { 'name': 'Person', 'age': 34 }
    # Hello {{ per.name }} {{ tl.clever_function('A', 'B') }}
    tm = env.get_template('test.txt.jinja')
    msg = tm.render(per=person)
    print(msg)
