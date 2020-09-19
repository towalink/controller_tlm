#!/bin/sh

# Workaround ignored sysctl.conf
sysctl -p

# Make sure all scripts are executable
chmod u+x /opt/towalink/startup/scripts/*

# Run all specific scripts
run-parts /opt/towalink/startup/scripts
echo "Running Towalink startup scripts done."
