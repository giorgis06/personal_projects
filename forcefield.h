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
            Eigen::Vector2d force = k*(-position+pose)/(pow((-position+pose).norm(),3));
            return force;
        }
};