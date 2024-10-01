#!/bin/bash
set -e

sudo chown -R $(whoami):$(whoami) /github

./setup.sh
./build.sh test
