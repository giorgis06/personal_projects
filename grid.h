#include <vector>
#include <algorithm>
#include <cmath>
#include <Eigen/Dense>
using Eigen::Vector2i;
using namespace std;

template<typename T>
class Grid{
    private:
        vector<vector<T*>> grid;
        int cols; int rows; float cell_size; int width; int height;
        
    public:
        Grid(int width, int height, float cell_size){
            if(cell_size == 0) terminate();
            this->width = width;
            this->height = height;
            this->cell_size = cell_size;
            cols = ceil(width/cell_size);
            rows = ceil(height/cell_size);
            grid.resize(cols * rows);
        }

        Vector2i grid_position(T& element){
            // x is column, y is row
            int x = int(element.getPos().x() / (double)cell_size);
            int y = int(element.getPos().y() / (double)cell_size);

            x = std::clamp(x, 0, cols - 1);
            y = std::clamp(y, 0, rows - 1);
            
            return Vector2i(x, y);
        }

        void add(T& element) { 
            getCell(grid_position(element)).push_back(&element); 
        }
        
        void wipe(){
            for(auto& v : grid){
                v.clear();
            }
        }

        vector<T*>& getCell(const Vector2i& pos){
            // 1D mapping: y * cols + x
            return grid[pos.y() * cols + pos.x()];
        }
        
        vector<vector<T*>> getAdjacents(T& element){
            vector<vector<T*>> adj;
            adj.reserve(9);
            
            Vector2i center = grid_position(element);
            
            // Loop using x (cols) and y (rows)
            for(int x = max(0, center.x() - 1); x <= min(center.x() + 1, cols - 1); x++){
                for(int y = max(0, center.y() - 1); y <= min(center.y() + 1, rows - 1); y++){
                    adj.push_back(getCell(Vector2i(x, y)));
                }
            }
            return adj;
        }
};