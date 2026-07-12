#pragma once
#include <memory>
#include <array>
#include <cmath>
#include <Eigen/Dense>
using Eigen::Vector2d;

// Barnes-Hut quadtree: O(N log N) approximation of N-body forces.
// Groups distant particles into a single point mass (their center of mass)
// once a node's region is small enough relative to its distance from the
// particle being evaluated (the theta criterion).
template<typename T>
class BarnesHutTree{
    private:
        struct Node{
            Vector2d center;
            double half_size;

            double total_mass = 0.0;
            Vector2d center_of_mass = Vector2d::Zero();

            T* particle = nullptr;
            std::array<std::unique_ptr<Node>, 4> children{};

            Node(Vector2d c, double hs) : center(c), half_size(hs) {}

            bool isLeaf() const { return children[0] == nullptr; }
        };

        std::unique_ptr<Node> root;
        static constexpr int MAX_DEPTH = 20;

        // Which of the 4 quadrants does pos fall in, relative to node's center.
        // bit 0 = right half, bit 1 = bottom half -> 0..3
        int quadrantOf(Node* node, const Vector2d& pos) const{
            int idx = 0;
            if(pos.x() > node->center.x()) idx |= 1;
            if(pos.y() > node->center.y()) idx |= 2;
            return idx;
        }

        Vector2d childCenter(Node* node, int idx) const{
            double q = node->half_size / 2.0;
            double dx = (idx & 1) ? q : -q;
            double dy = (idx & 2) ? q : -q;
            return node->center + Vector2d(dx, dy);
        }

        void subdivide(Node* node){
            for(int i = 0; i < 4; i++){
                node->children[i] = std::make_unique<Node>(childCenter(node, i), node->half_size / 2.0);
            }
        }

        void insert(Node* node, T* p, int depth){
            // Case 1: empty leaf -> this is the particle's home, done.
            if(node->isLeaf() && node->particle == nullptr){
                node->particle = p;
                node->total_mass = p->getMass();
                node->center_of_mass = p->getPos();
                return;
            }

            // Case 2: occupied leaf -> split into 4 children and re-home
            // both the existing occupant and the new particle.
            if(node->isLeaf()){
                if(depth >= MAX_DEPTH){
                    // Particles are (near-)coincident and would recurse forever.
                    // Merge them into this leaf's aggregate instead of splitting.
                    double m1 = node->total_mass, m2 = p->getMass();
                    node->center_of_mass = (node->center_of_mass * m1 + p->getPos() * m2) / (m1 + m2);
                    node->total_mass += m2;
                    return;
                }

                T* existing = node->particle;
                node->particle = nullptr;
                subdivide(node);

                insert(node->children[quadrantOf(node, existing->getPos())].get(), existing, depth + 1);
                insert(node->children[quadrantOf(node, p->getPos())].get(), p, depth + 1);
            }
            // Case 3: internal node -> descend into the correct child.
            else{
                insert(node->children[quadrantOf(node, p->getPos())].get(), p, depth + 1);
            }

            // Cases 2 and 3 both add one new particle (p) to a node that
            // already aggregated everything else beneath it. Fold p in.
            double m1 = node->total_mass, m2 = p->getMass();
            node->center_of_mass = (node->center_of_mass * m1 + p->getPos() * m2) / (m1 + m2);
            node->total_mass += m2;
        }

        // Returns the ACCELERATION contribution on p from everything under node
        // (already divided by p's own mass - matches Particle::time_step, which
        // expects acc directly, no further division needed).
        Vector2d computeForce(Node* node, const T& p, double theta, double G) const{
            if(node == nullptr || node->total_mass == 0.0) return Vector2d::Zero();

            // A leaf holding exactly this particle contributes nothing (no self-force).
            if(node->isLeaf() && node->particle == &p) return Vector2d::Zero();

            Vector2d r = node->center_of_mass - p.getPos();
            double dist = r.norm();
            if(dist < 1e-6) return Vector2d::Zero(); // guard against singularity

            // Leaves are always exact (nothing left to subdivide into).
            if(node->isLeaf()){
                return G * node->total_mass * r / (dist * dist * dist);
            }

            // Opening-angle criterion: s/d < theta means this cluster is either
            // small or far enough away to treat as one point mass.
            double s = node->half_size * 2.0;
            if(s / dist < theta){
                return G * node->total_mass * r / (dist * dist * dist);
            }

            // Otherwise the cluster is too close/large to approximate safely -
            // recurse into its children for a more detailed breakdown.
            Vector2d total = Vector2d::Zero();
            for(auto& child : node->children){
                total += computeForce(child.get(), p, theta, G);
            }
            return total;
        }

    public:
        // center/half_size define the square region the tree covers - must
        // enclose every particle that will be inserted this frame.
        BarnesHutTree(Vector2d center, double half_size){
            root = std::make_unique<Node>(center, half_size);
        }

        BarnesHutTree(double width, double height){
            double half_size = std::max(width, height) / 2.0;
            root = std::make_unique<Node>(Vector2d(width / 2.0, height / 2.0), half_size);
        }

        void insert(T& p){
            insert(root.get(), &p, 0);
        }

        // theta: opening angle threshold (smaller = more accurate, slower;
        // larger = faster, coarser). G: the force constant, applied uniformly.
        Vector2d computeForce(const T& p, double theta, double G) const{
            return computeForce(root.get(), p, theta, G);
        }
};
