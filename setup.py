import os
import setuptools


with open('README.md', 'r') as f:
    long_description = f.read()

setup_kwargs = {
    'name': 'towalink_tlm',
    'version': '0.1.6',
    'author': 'The Towalink Project',
    'author_email': 'pypi.tlm@towalink.net',
    'description': 'command line tool for configuring and managing a Towalink installation',
    'long_description': long_description,
    'long_description_content_type': 'text/markdown',
    'url': 'https://www.towalink.net',
    'packages': setuptools.find_packages('src'),
    'package_dir': {'': 'src'},
    'include_package_data': True,
    'install_requires': ['python-configuration',
                         'jinja2',
                         'pyyaml',
                         'toml',
                         'tomlkit',
                         'ansible',
                         'wgconfig>=0.1.4'
                        ],
    'entry_points': '''
        [console_scripts]
        tlm=tlm:main
    ''',
    'classifiers': [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: POSIX :: Linux',
        #'Development Status :: 2 - Pre-Alpha',
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Telecommunications Industry',
        'Topic :: System :: Networking'
    ],
    'python_requires': '>=3.6',
    'keywords': 'Towalink VPN SD-WAN WireGuard',
    'project_urls': {
        'Project homepage': 'https://www.towalink.net',
        'Repository': 'https://www.github.com/towalink/tlm',
        'Documentation': 'https://towalink.readthedocs.io',
    },
}


if __name__ == '__main__':
    setuptools.setup(**setup_kwargs)
