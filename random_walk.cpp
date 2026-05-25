#include <iostream>
#include <random>
#include <memory>
#include <string>
#include <algorithm>
#include <vector>
#include <SFML/Graphics.hpp>
#include <utility>
using namespace std;

class point{
    private:
        struct Position{
            int x,y;
            Position(int x = 0, int y = 0):x(x),y(y){}
            friend ostream& operator<<(ostream &out,Position &p){
                out << "(" << p.x << "," << p.y << ")";
                return out; 
            };
            void updatePos(int xplus,int yplus){
                x +=xplus; y += yplus;
            }
            void setPos(int xnew,int ynew){
                x = xnew; y = ynew;
            }
        };
        string id;
        Position pos;
    public:
        point(const string &name = "john doe",int x=0, int y=0):id(name){
            pos = Position(x,y);
            cout << "Initialized point " << name << " at " <<  pos;
        }

        void update(mt19937& engine){
            uniform_int_distribution<int> dist(0,3);
            switch(dist(engine)){
                case 0:
                    pos.updatePos(0,1);
                    break;
                case 1:
                    pos.updatePos(1,0);
                    break;
                case 2:
                    pos.updatePos(0,-1);
                    break;
                case 3:
                    pos.updatePos(-1,0);
                    break;
            }
        }
        pair<int,int> getPos(){
            return {pos.x,pos.y};
        }
};

void randomWalk(int walker_num =0){
    //STANARD RANDOM WALK - SET OF N POINTS MOVES IN A GRID IN SEQUENCE
    const int window_width = 800;
    const int window_height = 800;
    sf::RenderWindow window(sf::VideoMode(window_width, window_height), "Stochastic Random Walk");
    window.setFramerateLimit(60);

    random_device rd;
    mt19937 engine(rd());

    vector<point> walkers;
    vector<sf::VertexArray> paths(walker_num, sf::VertexArray(sf::LineStrip));
    vector<sf::CircleShape> particles(walker_num);
    vector<sf::Vector2f> start_pos;
    
    const float step_scale = 5.0f;
    const int start_x = window_width / 2;
    const int start_y = window_height / 2;

    for (int i = 0; i < walker_num; i++) {
        // Use to_string to properly name them "Walker 0", "Walker 1", etc.
        walkers.emplace_back("Walker " + to_string(i), 0, 0); 
        
        // Setup initial visual paths
        sf::Vector2f start_screen_pos(start_x, start_y);
        
        // Give each walker a slightly different color based on its index
        sf::Color pathColor(50, 100 + (i * 10) % 155, 200); 
        paths[i].append(sf::Vertex(start_screen_pos, pathColor));

        // Setup particles
        particles[i].setRadius(3.0f);
        particles[i].setFillColor(sf::Color::Red);
        particles[i].setOrigin(3.0f, 3.0f);
        particles[i].setPosition(start_screen_pos);
    }

            
    while(window.isOpen()){
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.type == sf::Event::Closed) {
                window.close();
            }
        }
        window.clear(sf::Color::White);
        
        for(int i = 0; i < walker_num; i++){
            walkers[i].update(engine);
            pair<int,int> grid_pos = walkers[i].getPos();

            sf::Vector2f screen_pos(
                start_x + (grid_pos.first * step_scale),
                start_y + (grid_pos.second * step_scale)
            );
            paths[i].append(sf::Vertex(screen_pos, sf::Color(50, 100 + (i * 10) % 155, 200)));
            particles[i].setPosition(screen_pos);

            // Render
            window.draw(paths[i]);
            window.draw(particles[i]);

        }
        window.display();
    }
}
   


int main(){
    randomWalk(100);
}