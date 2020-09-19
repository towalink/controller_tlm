#!/usr/bin/env python3

"""exceptionlogger.py: Runs a function and logs all exceptions to file"""

import datetime
import logging
import traceback


EXCEPTION_PATH = '/var/log/towalink_exceptions'
logger = logging.getLogger(__name__);


def call(func, *args, reraise_exceptions=True, **kwargs):
    """Runs a given function and logs all exceptions to file"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        # Print exceptions and log to file
        logger.critical('Exception occured: [{0}]'.format(e))
        logger.exception('Exception info:')  # just error but prints traceback
        with open(EXCEPTION_PATH, 'a') as handle:
            handle.write(datetime.datetime.now().isoformat(sep=' '))
            handle.write('\n')
            traceback.print_exc(file=handle)
            handle.write('\n')
        if reraise_exceptions:
            raise
