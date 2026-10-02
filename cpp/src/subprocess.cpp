#include "pareto_nbd/subprocess.hpp"

#include <chrono>
#include <thread>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <csignal>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace pareto_nbd {

#ifdef _WIN32
namespace {
// Standard CommandLineToArgvW-compatible quoting.
std::string QuoteArg(const std::string& a) {
    std::string out = "\"";
    size_t bs = 0;
    for (char c : a) {
        if (c == '\\') {
            ++bs;
        } else if (c == '"') {
            out.append(bs * 2 + 1, '\\');
            out += '"';
            bs = 0;
        } else {
            out.append(bs, '\\');
            bs = 0;
            out += c;
        }
    }
    out.append(bs * 2, '\\');
    out += '"';
    return out;
}
}  // namespace

SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds) {
    SubprocessResult r;
    if (argv.empty()) return r;
    std::string cmd;
    for (const auto& a : argv) {
        if (!cmd.empty()) cmd += ' ';
        cmd += QuoteArg(a);
    }
    STARTUPINFOA si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    if (!CreateProcessA(nullptr, cmd.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr,
                        nullptr, &si, &pi)) {
        return r;
    }
    r.launched = true;
    DWORD w = WaitForSingleObject(pi.hProcess, static_cast<DWORD>(timeout_seconds) * 1000);
    if (w == WAIT_TIMEOUT) {
        TerminateProcess(pi.hProcess, 1);
        WaitForSingleObject(pi.hProcess, 5000);
        r.timed_out = true;
    } else {
        DWORD code = 0;
        GetExitCodeProcess(pi.hProcess, &code);
        r.exit_code = static_cast<int>(code);
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return r;
}
#else
SubprocessResult RunWithTimeout(const std::vector<std::string>& argv, int timeout_seconds) {
    SubprocessResult r;
    if (argv.empty()) return r;
    std::vector<char*> args;
    for (const auto& a : argv) args.push_back(const_cast<char*>(a.c_str()));
    args.push_back(nullptr);
    pid_t pid = fork();
    if (pid < 0) return r;
    if (pid == 0) {
        execvp(args[0], args.data());
        _exit(127);
    }
    r.launched = true;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(timeout_seconds);
    int status = 0;
    while (true) {
        pid_t done = waitpid(pid, &status, WNOHANG);
        if (done == pid) {
            r.exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
            return r;
        }
        if (std::chrono::steady_clock::now() >= deadline) {
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            r.timed_out = true;
            return r;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}
#endif

}  // namespace pareto_nbd
