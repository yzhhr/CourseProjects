#include <iostream>
#include <list>
#include <vector>
#include <cassert>
#include <tuple>
#include <random>

struct Block {
    int size;
    bool free;
    int offset;
    std::list<Block*>::iterator in_allblocks;
    std::list<Block*>::iterator in_hierachy;
    Block(int size, bool free, int offset) : size(size), free(free), offset(offset) {}
    int logsize() {
        // std::cout << "size=" << size << std::endl;
        assert(__builtin_popcount(size) == 1);
        return __builtin_ctz(size);
    }
    bool isleft() {
        return offset / size % 2 == 0;
    }
    // print related
    void print() {
        std::cout << "Block: size=" << size << " free=" << free << " offset=" << offset << std::endl;
    }
};
std::list<Block*> allblocks;

int log(int x) {
    assert(__builtin_popcount(x) == 1);
    return __builtin_ctz(x);
}

class BlockManager {
    // take from front, free to back
    std::vector< std::list<Block*> > hierachy;
    // requested <= allocated <= total
    // requested is the sum of user requested sizes
    // allocated is the sum of allocated blocks to user requests
    int total, allocated, requested;
    bool yes2, yes4;
public:
    BlockManager() {
        this->yes2 = true;
        this->yes4 = true;
    }

    void set_24(bool yes2, bool yes4) {
        this->yes2 = yes2;
        this->yes4 = yes4;
    }

    double usage() {
        return (double)requested / allocated;
    }

    void init(int total) {
        assert(__builtin_popcount(total) == 1);
        hierachy.clear();
        for (Block *b : allblocks) {
            delete b;
        }
        allblocks.clear();
        Block *b = new Block(total, true, 0);
        allblocks.push_back(b);
        
        hierachy.resize(log(total) + 1);
        hierachy[b->logsize()].push_back(b);
        b->in_allblocks = allblocks.begin();
        b->in_hierachy = hierachy[b->logsize()].begin();

        this->total = total;
        this->allocated = 0;
        this->requested = 0;
    }

    // returns the position in allblocks
    std::list<Block *>::iterator remove(Block *b) {
        auto it = allblocks.erase(b->in_allblocks);
        hierachy[b->logsize()].erase(b->in_hierachy);
        delete b;
        return it;
    }

    // `it` is the position in allblocks
    void insert(Block *b, std::list<Block *>::iterator it) {
        allblocks.insert(it, b);
        b->in_allblocks = std::prev(it);
        b->in_hierachy = hierachy[b->logsize()].insert(hierachy[b->logsize()].begin(), b);
    }

    std::pair< Block*, Block* >
        split(Block *b) {
            // split the block into two blocks, evenly
            Block *l = new Block(b->size / 2, true, b->offset);
            Block *r = new Block(b->size / 2, true, b->offset + b->size / 2);
            auto it = remove(b);
            insert(l, it);
            insert(r, it);
            return std::make_pair(l, r);
        }
    
    Block* merge(Block *l, Block *r) {
        // std::cout << "merge" << std::endl;
        // l->print();
        // r->print();
        assert(l->free && r->free);
        assert(l->size == r->size);
        assert(l->offset + l->size == r->offset);
        assert(r->in_allblocks == std::next(l->in_allblocks));
        assert(l->isleft());
        assert(!r->isleft());
        Block *b = new Block(l->size * 2, true, l->offset);
        auto it = remove(l);
        it = remove(r);
        insert(b, it);
        return b;
    }

    void alloc(Block *b) {
        assert(b->free);
        b->free = false;
        hierachy[b->logsize()].erase(b->in_hierachy);
    }
    
    void free(Block *b) {
        assert(!b->free);
        b->free = true;
        hierachy[b->logsize()].push_back(b);
        b->in_hierachy = hierachy[b->logsize()].end();
        b->in_hierachy--;

        while(true) {
            if (b->logsize() == hierachy.size() - 1) {
                break; // already the largest block
            }
            if (b->isleft()) { // self is left
                Block *r = *std::next(b->in_allblocks);
                if (r->size != b->size) break;
                if (!r->free) break;
                b = merge(b, r);
            } else { // self is right
                Block *l = *std::prev(b->in_allblocks);
                if (l->size != b->size) break;
                if (!l->free) break;
                b = merge(l, b);
            }
        }
    }

    std::vector<Block*> alloc(int request_size) {
        int size = request_size;
        std::vector<Block*> result;
        int level = 0;
        while ((1 << level) < size || hierachy[level].empty()) {
            level++;
            if (level == hierachy.size()) {
                return result; // no enough memory
            }
        }
        Block *b = hierachy[level].front();
        while (true) {
            // std::cout << "size=" << size << " b->size=" << b->size << std::endl;
            if (this->yes2 && b->size >= size * 2) {
                Block *l, *r;
                std::tie(l, r) = split(b);
                b = l;
            } else if (this->yes4 && b->size * 3 >= size * 4) {
                Block *l, *r;
                std::tie(l, r) = split(b);
                Block *r1, *r2;
                std::tie(r1, r2) = split(r);
                result.push_back(l);
                alloc(l);
                b = r1;
            } else {
                result.push_back(b);
                alloc(b);
                break;
            }
        }
        this->requested += request_size;
        for (Block *b : result) {
            this->allocated += b->size;
        }
        return result;
    }

    void free(int requested, std::vector<Block*> blocks) {
        this->requested -= requested;
        for (Block *b : blocks) {
            this->allocated -= b->size;
            free(b);
        }
    }
};

std::pair<double, double> test(int num_rounds=10000, bool yes4=true) {
    BlockManager bm;
    bm.init(4096);
    bm.set_24(true, yes4);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 1024);
    dis(gen);
    int total_requests = 0, accepted_requests = 0;
    double highest_usage = 0;
    double sum_usage = 0;
    int num_usage = 0;
    auto sample_request = [&gen](){
        std::uniform_int_distribution<> dis(1, 10);
        int logsize = dis(gen);
        std::uniform_int_distribution<> dis2(1 << logsize, 1 << (logsize + 1));
        return dis2(gen);
    };
    auto randint = [&gen](int l, int r) {return 1;
        std::uniform_int_distribution<> dis(l, r);
        return dis(gen);
    };
    std::vector< std::pair<int, std::vector<Block*> > > allocated_blocks;
    for (int i = 0; i < num_rounds; i++) {
        if (i % 3 != 0) {
            int request_size = sample_request();
            total_requests ++;
            std::vector<Block*> blocks = bm.alloc(request_size);
            if (blocks.empty()) {
                continue;
            }
            allocated_blocks.push_back(std::make_pair(request_size, blocks));
            accepted_requests ++;
            if (bm.usage() > highest_usage) {
                highest_usage = bm.usage();
            }
            sum_usage += bm.usage();
            num_usage++;
        } else {
            if (allocated_blocks.empty()) {
                continue;
            }
            int idx = randint(0, allocated_blocks.size() - 1);
            int request_size = allocated_blocks[idx].first;
            std::vector<Block*> &blocks = allocated_blocks[idx].second;
            bm.free(request_size, blocks);
            std::swap(allocated_blocks[idx], allocated_blocks.back());
            allocated_blocks.pop_back();
        }
    }
    // std::cout << "total requests: " << total_requests << std::endl;
    // std::cout << "accepted requests: " << accepted_requests << std::endl;
    // std::cout << "highest usage: " << highest_usage << std::endl;
    // std::cout << "average usage: " << sum_usage / num_usage << std::endl;
    return std::make_pair((double)accepted_requests / total_requests, sum_usage / num_usage);
}

int main() {
    std::cout.precision(3);
    for (int i = 0; i < 6; i++) {
        auto it = test(1000000, true);
        std::cout << it.second << " | ";
    }
    std::cout << std::endl;
    for (int i = 0; i < 6; i++) {
        auto it = test(1000000, false);
        std::cout << it.second << " | ";
    }
    // auto it = test(1000000, true);
    // std::cout << "yes4: " << it.first << " " << it.second << std::endl;
    // auto it2 = test(1000000, false);
    // std::cout << "no4: " << it2.first << " " << it2.second << std::endl;
    return 0;
}
