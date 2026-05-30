#include "particle.h"
#include "grid.h"
#include <random>


void simulation_step(vector<Particle>& particles,Grid<Particle>& grid,sf::RenderWindow& window,double dt = 1){
    //FORCE FIELD UPDATES ACCELERATIONS IF NEEDED
    
    for(auto& p : particles){
        p.time_step(dt);
        p.out_of_bounds(window);
    }
    grid.wipe();
    for(auto &p:particles){
        grid.add(p);
    }    

    // FOR EVERY PARTICLE
    for(auto&p:particles){
        // FIND ITS ADJACENT CELLS
        for(auto& cell:grid.getAdjacents(p)){
            // FOR EVERY CELL
            for(auto& q: cell){
                // RESOLVE THE COLLISIONS INSIDE THE CELL
                if(&p < q) resolveCollision(p,*q);
                // LESSER THAN TO SIMULTANEOUSLY PREVENT SELF-COLLISIONS AND
                // THE SAME COLLISION BEING CHECKED TWICE
                // EITHER < OR > WILL HOLD FOR ADDRESSES, THEREFORE
                // THE PAIR WILL ONLY BE CHECKED ONCE, SAVING PROCESSING TIME
            }
        }
    }
}

int main(){
    double dt = 0.1/60;
    const int N = 500;

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
        cell_size = max(cell_size,5*r); //maximum particle diameter defines cell size
        float m = 1.0;
        float e = (float)(0.1*abs(dist(generator)));
        Eigen::Vector2d vel(40*static_cast<float>(dist(generator)),40*static_cast<float>(dist(generator)));
        Eigen::Vector2d pos(400+10*static_cast<float>(dist(generator)),400+10*static_cast<float>(dist(generator)));
        particles.emplace_back(Particle(r,m,e,pos,vel));
    }

    // GRID DEFINITION AND RESIZING, CEILING OF LENGTH/MAXIMUM CELL SIZE
    // 1D VECTOR MIMICKING 2D MESH, ACCESS WITH J*COLS + I
    Grid<Particle> grid(window_width,window_height,cell_size);
    for(auto&p:particles){
        grid.add(p);
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
        for(int i = 0; i < 10; i++){
            simulation_step(particles,grid,window,dt);
        }
        for(auto&p:particles) p.draw(window);
        
        window.display();
    }
}