#!/bin/bash

bash build.sh
colcon test --merge-install
colcon test-result --all
