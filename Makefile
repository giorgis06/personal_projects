CXX := g++
CXXFLAGS := -std=c++17 -I/usr/include/eigen3
LDLIBS := -lsfml-graphics -lsfml-window -lsfml-system

.PHONY: all clean

all: sim random_walk

sim: particle_simulation.cpp particle.h grid.h forcefield.h
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

random_walk: random_walk.cpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

clean:
	rm -f sim random_walk
