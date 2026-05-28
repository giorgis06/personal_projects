#include <iostream>
#include <vector>
#include <cmath>
#include <SFML/Graphics.hpp>
#include <Eigen/Dense>
#include "forcefield.h"

using namespace std;

/*
    ****PARTICLE CLASS****
Objects with mass, radius, position, velocity and acceleration.

Methods which calculate acceleration based on the force enacted upon them by forcefields 
(possible extension - adding a force field for every particle as a parameter, maybe in the future)

Collision detection and resolution methods using a certain restitution coefficient, with tweaks to make collisions more realistic

More to be added
*/

class Particle {
private:
    // Physics State (Double precision for mathematical stability)
    Eigen::Vector2d pos;
    Eigen::Vector2d vel;
    Eigen::Vector2d acc;
    
    double mass;
    double radius;
    double restitution;
    int name;
    
    // Visual State (SFML uses floats for rendering)
    sf::CircleShape circle;

public:
    Particle(double radius,int n, double m = 1.0, double rest = 1.0,
             const Eigen::Vector2d& position = Eigen::Vector2d::Zero(), 
             const Eigen::Vector2d& velocity = Eigen::Vector2d::Zero())
        : pos(position), vel(velocity), acc(Eigen::Vector2d::Zero()), name(n), mass(m), radius(radius),restitution(rest)
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
    double getRest() const { return restitution; }
    double getMass() const { return mass; }

    //Setters
    void setPos(const Eigen::Vector2d& new_pos) { pos = new_pos; }
    void setVel(const Eigen::Vector2d& new_vel) { vel = new_vel; }
    void applyForce(Force_Field &force) { acc += force.getForce(pos) / mass; }

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

    friend bool operator!=(const Particle &p1,const Particle &p2){
        return p1.name != p2.name;
    }

    // --- Collision Detection ---
    friend bool collision(Particle& p1, Particle& p2) {
        // Eigen's squaredNorm() avoids the expensive square root operation!
        double dist_squared = (p1.pos - p2.pos).squaredNorm();
        double radius_sum = p1.radius + p2.radius;
        return dist_squared <= (radius_sum * radius_sum);
    }

    // --- Collision Resolution (Math applied) ---
    friend void resolveCollision(Particle& p1, Particle& p2) {
        if (!collision(p1, p2) || p1.name == p2.name) return;
        
        //Define normal vector on which collision occurs
        Eigen::Vector2d n = (p1.getPos()-p2.getPos()).normalized();
        //Find relative velocity parallel to normal vector
        double relVel = (p1.getVel()-p2.getVel()).dot(n);
        
        //If positive, then particles are moving away from each other, return;
        if(relVel>=0) return;
        //If negative, then collision is happening, resolve with formula and restitution coefficient
        double e = std::min(p1.getRest(), p2.getRest());

        Eigen::Vector2d vel1 = ((p1.getMass() - e * p2.getMass()) * p1.getVel().dot(n) + p2.getMass() * (1 + e) * p2.getVel().dot(n)) / (p1.getMass() + p2.getMass())*n;
        Eigen::Vector2d vel2 = ((p2.getMass() - e * p1.getMass()) * p2.getVel().dot(n) + p1.getMass() * (1 + e) * p1.getVel().dot(n)) / (p1.getMass() + p2.getMass())*n;

        p1.setVel(p1.getVel()-p1.getVel().dot(n)*n + vel1);
        p2.setVel(p2.getVel()-p2.getVel().dot(n)*n + vel2);

        //correct positions if the two overlap
        // Only correct if the overlap is noticeable (slop)
        double depth = p1.getRadius()+p2.getRadius()-(p1.getPos()-p2.getPos()).norm();

        const double slop = 0.05; 
        const double percent = 0.8; //only correct 80% of the depth to prevent bouncy jitter

        if (depth > slop) {
            double invMass1 = 1.0 / p1.getMass();
            double invMass2 = 1.0 / p2.getMass();
            double sumInvMass = invMass1 + invMass2;

            // Divide the depth by total inverse mass, apply percent dampening
            Eigen::Vector2d correction = ((depth - slop )/ sumInvMass) * percent * n;

            // Push apart weighted by mass (heavy objects move less)
            p1.setPos(p1.getPos() + invMass1 * correction);
            p2.setPos(p2.getPos() - invMass2 * correction);
        }

    }
};