#!/bin/bash
set -e

git config --global --add safe.directory /github/workspace

./setup.sh
./build.sh test
