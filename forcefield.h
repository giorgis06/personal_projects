#include <Eigen/Dense>

class Force_Field{
    private:
        //value of force at every point
        //possibly a formula for calculating it?
        //function definition
        Eigen::Vector2d force;
    public:
        Force_Field(const Eigen::Vector2d& f = Eigen::Vector2d::Zero()):force(f){}

        Eigen::Vector2d getForce(const Eigen::Vector2d& position) const{
            //calculate force at point via given formula. maybe make 
            //separate constructors for different fundamental forces?
            return force;
        }
};