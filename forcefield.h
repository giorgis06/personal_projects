#include <Eigen/Dense>
#include <cmath>
#include <memory>
using namespace std;

//possibly define a function class which will allow for exotic forces 
//of the users' taste!

class Force_Field{
    private:
        const double k;
        Eigen::Vector2d pose;
    public:
        Force_Field(const double& constant = -1.0,const Eigen::Vector2d& pos = Eigen::Vector2d::Zero()):k(constant),pose(pos){}

        Eigen::Vector2d getForce(const Eigen::Vector2d& position){
            //regular square law, might expand in the future to cover more potentials
            Eigen::Vector2d r = pose - position; 
            double dist = r.norm();

            // Prevent division by zero if particle is exactly at the center
            if (dist < 0.01) return Eigen::Vector2d::Zero(); 

            return k * r / (dist * dist * dist);
        }
};