#include <Eigen/Dense>
#include <cmath>
#include <memory>
using namespace std;

class Force_Field{
    private:
        //value of force at every point
        //possibly a formula for calculating it?
        //function definition
        const double k;
        Eigen::Vector2d pose;
    public:
        Force_Field(const double& constant = -1.0,const Eigen::Vector2d& pos = Eigen::Vector2d::Zero()):k(constant),pose(pos){}

        Eigen::Vector2d getForce(const Eigen::Vector2d& position) const{
            Eigen::Vector2d force = k*(-position+pose)/(pow((-position+pose).norm(),3))
            return force;
        }
};