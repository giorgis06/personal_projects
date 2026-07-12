#!/bin/bash
cd "$(dirname "$0")"
g++ -I/usr/include/eigen3 particle_simulation.cpp -o sim -lsfml-graphics -lsfml-window -lsfml-system
./sim