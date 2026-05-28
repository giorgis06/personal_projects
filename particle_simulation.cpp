#include "particle.h"
#include <random>

void simulation_step(vector<Particle>& particles,sf::RenderWindow& window,double dt = 1){
    //FORCE FIELD UPDATES ACCELERATIONS IF NEEDED
    
    for(auto& p : particles){
        p.time_step(dt);
    }
        
    for(auto& p : particles){
        for(auto&q : particles){
            resolveCollision(p,q);
        }
    }

    for(auto& p: particles){
        p.draw(window);
    }
}

int main(){
    double dt = 0.01;
    const int N = 10;
    random_device rd;
    default_random_engine generator(rd());

    uniform_int_distribution<int> dist(-10,10);

    const int window_width = 800;
    const int window_height = 800;
    sf::RenderWindow window(sf::VideoMode(window_width, window_height), "Simulation");
    window.setFramerateLimit(60);


    vector<Particle> particles;
    for(int i = 0; i < N; i++){
        Eigen::Vector2d position(400+10*static_cast<float>(dist(generator)),400+10*static_cast<float>(dist(generator)));
        Eigen::Vector2d vel(10*static_cast<float>(dist(generator)),10*static_cast<float>(dist(generator)));
        particles.emplace_back(Particle(abs(static_cast<float>(dist(generator))),i,1.0,1.0,position,vel));
    }

    
    while(window.isOpen()){
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.type == sf::Event::Closed) {
                window.close();
            }
        }
        window.clear(sf::Color::White);

        simulation_step(particles,window,dt);
        window.display();
    }
}