#include "particle.h"
#include <random>

void simulation_step(vector<Particle>& particles,sf::RenderWindow& window,double dt = 1){
    //FORCE FIELD UPDATES ACCELERATIONS IF NEEDED
    
    for(auto& p : particles){
        p.time_step(dt);
        p.out_of_bounds(window);
    }
        
    
    for (size_t i = 0; i < particles.size(); i++) {
        for (size_t j = i + 1; j < particles.size(); j++) {
            resolveCollision(particles[i], particles[j]);
    }
}
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


    vector<Particle> particles;
    for(int i = 0; i < N; i++){
        Eigen::Vector2d position(400+10*static_cast<float>(dist(generator)),400+10*static_cast<float>(dist(generator)));
        Eigen::Vector2d vel(30*static_cast<float>(dist(generator)),30*static_cast<float>(dist(generator)));
        particles.emplace_back(Particle(5,i,abs(static_cast<float>(dist(generator))),
                                        0.69,
                                        position,vel));
    }
    
    while(window.isOpen()){
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.type == sf::Event::Closed) {
                window.close();
            }
        }
        window.clear(sf::Color::White);
        for(int i = 0; i < 100; i++){
            simulation_step(particles,window,dt);
        }
        
        window.display();
    }
}