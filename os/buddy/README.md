# Buddy system

A toy buddy system. Maintains a continuous memory space and allocates blocks of different sizes.

## Problem Statement

Implement the following improved buddy system using C or Rust language.

Modify buddy system allocation operations:

1. Find the smallest available block in the free blocks from smallest to largest;
2. If the free block is more than twice the size of the requested block, bisect the available free block until an appropriate available free block is obtained;
3. If the free block is more than 4/3 times the size of the requested block, quarter the available free block until an appropriate available free block is obtained.

Additionally, analyze the storage utilization rate and allocation/release overhead of the 'improved buddy system.

## Implementation

In `main.cpp` attached, a toy buddy system is implemented. The system maintains `std::list<Block*> allblocks` which is the linear arrangement of different sized blocks, as the order in the memory. Every block points to its previous and next adjacent block.

In the `BlockManager` we maintain `std::vector< std::list<Block*> > hierachy`, where `hierachy[i]` keeps track of all free blocks of size $2^i$.

Overhead of the system is proportional to the length of `hierachy`, or log of the maximum block size.

## Utilization

Here is the usage printed by the program. `2split and 4 split` denotes the complete heuristics. `2split` only splits an interval when `interval size >= 2 * requested size`.

In the following `storage utilization rate` is calculated as average of `total_requested_size / total_allocated_size`, because the algorithm may allocate a whole block that is slightly more than requested size.

| Trial | 2split and 4split | 2split only |
|-------|------------------|-------------|
|   1   |      0.920       |    0.678    |
|   2   |      0.835       |    0.780    |
|   3   |      0.878       |    0.753    |
|   4   |      0.858       |    0.718    |
|   5   |      0.881       |    0.831    |
|   6   |      0.872       |    0.809    |

## Weaknesses

The `hierachy` is taken from the front when there is a request, and inserted at the back when some block is freed. Maybe a better strategy exists.

The test cases are generated that every request size is uniformly taken from log $[1, 2^B]$, so that the interval 512-1024 is equally likely to be selected as the interval 4-8. Then the utilization is tested as long-term full-load average. This may not be a good representation of the real-world scenario.

## Appendix: 

```txt
### 第 10 次课后练习

#### 第 1 题

用 C 或 Rust 语言实现如下的改进伙伴系统。

修改伙伴系统分配操作：

1. 由小到大在空闲块中找最小可用块；
2. 如空闲块大于申请块的二倍，对可用空闲块进行二等分，直到得到合适可用空闲块；
3. 如空闲块大于申请块的 4/3，对可用空闲块进行四等分，直到得到合适可用空闲块。

并分析“改进伙伴系统”的存储利用率和分配释放开销。
```
