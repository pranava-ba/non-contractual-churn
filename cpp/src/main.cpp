#include <iostream>
#include "pareto_nbd/version.hpp"

int main() {
    std::cout << "pareto-nbd-inference v" << pareto_nbd::version() << "\n";
    return 0;
}
