#include <iostream>
#include <vector>
#include <cmath>
#include <SFML/Graphics.hpp>
#include <Eigen/Dense>
#include "forcefield.h"

using namespace std;

class Particle {
private:
    // Physics State (Double precision for mathematical stability)
    Eigen::Vector2d pos;
    Eigen::Vector2d vel;
    Eigen::Vector2d acc;
    
    double mass;
    double radius;
    
    // Visual State (SFML uses floats for rendering)
    sf::CircleShape circle;

public:
    Particle(double radius, double m = 1.0, 
             const Eigen::Vector2d& position = Eigen::Vector2d::Zero(), 
             const Eigen::Vector2d& velocity = Eigen::Vector2d::Zero())
        : pos(position), vel(velocity), acc(Eigen::Vector2d::Zero()), mass(m), radius(radius) 
    {
        // Replaced the broken printf with standard cout
        cout << "Generated particle at (" << pos.x() << ", " << pos.y() << ").\n";
        
        // Setup SFML visuals
        circle.setRadius(static_cast<float>(radius));
        circle.setFillColor(sf::Color::Cyan);
        circle.setOrigin(static_cast<float>(radius), static_cast<float>(radius));
        circle.setPosition(static_cast<float>(pos.x()), static_cast<float>(pos.y()));
    }

    //Getters
    Eigen::Vector2d getPos() const { return pos; }
    Eigen::Vector2d getVel() const { return vel; }
    double getRadius() const { return radius; }
    double getMass() const { return mass; }

    //Setters
    void setPos(const Eigen::Vector2d& new_pos) { pos = new_pos; }
    void setVel(const Eigen::Vector2d& new_vel) { vel = new_vel; }
    void applyForce(const Force_Field &force) { acc += force.getForce(pos) / mass; }

    //Euler implicit integration update
    void time_step(double dt) {
        vel += acc * dt;
        pos += vel * dt;
        
        //Reset acceleration for next time step
        acc.setZero(); 

        //Update visuals (cast to float for SFML)
        circle.setPosition(static_cast<float>(pos.x()), static_cast<float>(pos.y()));
    }

    void draw(sf::RenderWindow& window) const {
        window.draw(circle);
    }

    // --- Collision Detection ---
    friend bool collision(const Particle& p1, const Particle& p2) {
        // Eigen's squaredNorm() avoids the expensive square root operation!
        double dist_squared = (p1.pos - p2.pos).squaredNorm();
        double radius_sum = p1.radius + p2.radius;
        return dist_squared <= (radius_sum * radius_sum);
    }

    // --- Collision Resolution (Math applied) ---
    friend void resolveCollision(Particle& p1, Particle& p2) {
        if (!collision(p1, p2)) return;
        
        //Define normal vector on which collision occurs

        //Find relative velocity parallel to normal vector
        
        //If positive, then particles are moving away from each other, return;

        //If negative, then collision is happening, resolve with formula and restitution coefficient

        //Try to make it as fast as possible, since N*(N-1)/2 
        //will be happening every time step (N choose 2 pairs)
    }
};