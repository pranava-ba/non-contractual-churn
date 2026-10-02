#pragma once
#include <string>
#include <vector>

namespace pareto_nbd {

struct SubprocessResult {
    bool launched = false;   // false: the process could not be started at all
    bool timed_out = false;  // true: killed after exceeding timeout_seconds
    int exit_code = -1;      // valid only when launched && !timed_out
};

// Runs argv[0] with argv[1..] (resolved via PATH), waits up to timeout_seconds, kills the
// process if it is still running, and reports what happened. stdout/stderr are inherited.
SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds);

}  // namespace pareto_nbd
