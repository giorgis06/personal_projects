# Build and test entry point for fem_solver. Run from this folder.
#   make        -> ./fem
#   make test   -> builds and runs ./run_tests
#   make clean

CXX      := g++
# -fvisibility flags: without them the executable's inline gmsh::initialize
# (from the vendored gmsh.h) interposes libgmsh's own symbol -> infinite recursion.
CXXFLAGS := -std=c++17 -Wall -Wextra -fvisibility=hidden -fvisibility-inlines-hidden
CPPFLAGS := -I. -Imesh -Ilinalg -I.venv/include
LDFLAGS  := -L.venv/lib -Wl,-rpath,'$$ORIGIN/.venv/lib'
LDLIBS   := -lgmsh

# The pip gmsh wheel ships only the versioned libgmsh.so.4.x, which -lgmsh can't find.
GMSH_SO  := .venv/lib/libgmsh.so

HEADERS  := $(wildcard *.h */*.h */*/*.h)
TESTS    := $(wildcard tests/*.cpp)

.PHONY: all test clean

all: fem

fem: main.cpp mesh/mesh.cpp $(HEADERS) | $(GMSH_SO)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) main.cpp mesh/mesh.cpp $(LDFLAGS) $(LDLIBS) -o $@

run_tests: $(TESTS) mesh/mesh.cpp $(HEADERS) tests/doctest.h | $(GMSH_SO)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) $(TESTS) mesh/mesh.cpp $(LDFLAGS) $(LDLIBS) -o $@

test: run_tests
	./run_tests

$(GMSH_SO):
	ln -sf $$(basename $$(ls .venv/lib/libgmsh.so.* | head -1)) $@

clean:
	rm -f fem run_tests
