#!/bin/bash

/usr/bin/rsync "$@"
result=$?
(
  if [ $result -eq 0 ]; then
    if [ -f /opt/towalink/venv/bin/activate ]; then
      source /opt/towalink/venv/bin/activate
    fi
    nodeconfig -l debug >> /var/log/towalink_nodeconfig.log 2>&1
  fi
) >/dev/null 2>/dev/null </dev/null
exit $result
