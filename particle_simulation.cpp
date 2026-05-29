#include "particle.h"
#include <random>

vector<vector<unique_ptr<Particle>>> getAdjacents(int i, int j,int grid_cols,int grid_rows,vector<vector<unique_ptr<Particle>>>& grid){
    vector<vector<unique_ptr<Particle>>> adjacents(8);
    for(int x = max(0,j-1); x <= max(j+1,grid_cols-1); x++){
        for(int y = max(0,i-1); y <= max(i+1,grid_rows); y++){
            adjacents.push_back(grid[x+grid_cols*y]);
        }
    }
    return adjacents;
}
Eigen::Vector2i gridPos(Particle& p,double cell_size){
    int j = floor(p.getPos().x()/cell_size);
    int i = floor(p.getPos().y()/cell_size);
    return Eigen::Vector2i(i,j);
}


void simulation_step(vector<Particle>& particles,vector<vector<unique_ptr<Particle>>>& grid,int grid_cols,
                    int grid_rows,double cell_size,sf::RenderWindow& window,double dt = 1){
    //FORCE FIELD UPDATES ACCELERATIONS IF NEEDED
    
    for(auto& p : particles){
        p.time_step(dt);
        p.out_of_bounds(window);
    }
    
    for(auto&p : particles){
        int i = gridPos(p,cell_size).x();
        int j = gridPos(p,cell_size).y();
        vector<vector<unique_ptr<Particle>>> adj = getAdjacents(i,j,grid_cols,grid_rows,grid);
        for(auto& cell : adj){
            for(auto& particle_ptr : cell){
                resolveCollision(p,*particle_ptr);
            }
        }
    }    
    
    /*for (size_t i = 0; i < particles.size(); i++) {
        for (size_t j = i + 1; j < particles.size(); j++) {
            resolveCollision(particles[i], particles[j]); // O(N^2) - inneficient, must become O(N), by checking adjacency at the cost of memory
            
            // NEEDS MODIFICATION - CHANGE INTO A 2D MESH WHICH STORES POINTERS TO PARTICLES
            // IN EACH CELL, ALLOWING FOR A FASTER ITERATION, CHECKING ONLY THE PARTICLES
            // THAT ARE POSSIBLE TO BE COLLIDING (8 ADJACENT CELLS AROUND THE CURRENT ONE)
            // vector<vector<Particle*>> 1d array which has index access of grid.y*cols+grid.x
            // for container of particles of cell (x,y)
    }
    }*/
    for(auto& p: particles){
        p.draw(window);
    }
}

int main(){
    double dt = 0.01/60;
    const int N = 10;

    random_device rd;
    default_random_engine generator(rd());

    uniform_int_distribution<int> dist(-10,10);

    const int window_width = 800;
    const int window_height = 800;
    sf::RenderWindow window(sf::VideoMode(window_width, window_height), "Simulation");
    window.setFramerateLimit(60);

    float cell_size = 0.0;
    // generate particles with random characteristics
    vector<Particle> particles;
    for(int i = 0; i < N; i++){
        float r = 5.0;
        cell_size = max(cell_size,2*r); //maximum particle diameter defines cell size
        float m = 1.0;
        float e = 1.0;
        Eigen::Vector2d vel(30*static_cast<float>(dist(generator)),30*static_cast<float>(dist(generator)));
        Eigen::Vector2d pos(400+10*static_cast<float>(dist(generator)),400+10*static_cast<float>(dist(generator)));
        particles.emplace_back(Particle(r,i,m,e,pos,vel));
    }

    // GRID DEFINITION AND RESIZING, CEILING OF LENGTH/MAXIMUM CELL SIZE
    // 1D VECTOR MIMICKING 2D MESH, ACCESS WITH J*COLS + I
    vector<vector<unique_ptr<Particle>>> grid; 
    int cols = ceil(window_width / cell_size);
    int rows = ceil(window_height / cell_size);
    grid.resize(cols*rows);
    
    if(cell_size == 0) terminate(); // kind of bad, ought to change
    for(auto& p:particles){
        int i = gridPos(p,cell_size).x();
        int j = gridPos(p,cell_size).y();
        grid[i+cols*j].emplace_back(unique_ptr<Particle>(&p));
    }
    

    while(window.isOpen()){
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.type == sf::Event::Closed) {
                window.close();
            }
        }
        window.clear(sf::Color::White);
        // sub_steps between each frame, for higher accuracy
        for(int i = 0; i < 100; i++){
            simulation_step(particles,grid,cols,rows,cell_size,window,dt);
        }
        
        window.display();
    }
}