#pragma once
// 内部工具：方案输出回调多播器。
// VisionMasterCore 的 C 回调（SDK 工作线程）调用 dispatch()，
// 分发给所有已注册的 GlobalCameraCore 实例。注册/注销在用户线程进行。
// dispatch() 在无 GIL 的 SDK 工作线程上执行，处理函数禁止调用任何 Python API（pybind11 对象操作）。
#include <algorithm>
#include <condition_variable>
#include <mutex>
#include <vector>
#include "IVmExport.h"

namespace VMC
{
    class OutputHandler
    {
    public:
        virtual ~OutputHandler() = default;
        // 在 SDK 回调线程执行；禁止抛出异常、禁止调用 Python API
        virtual bool onOutput(OutputPlatformInfo *info) noexcept = 0;
    };

    class OutputDispatcher
    {
    public:
        static void registerHandler(OutputHandler *h)
        {
            std::lock_guard<std::mutex> lock(mutex());
            handlers().push_back(h);
        }

        // 禁止在 dispatch 回调上下文内调用（会等待自身 dispatch 结束而自死锁）
        static void unregisterHandler(OutputHandler *h)
        {
            std::unique_lock<std::mutex> lock(mutex());
            auto &hs = handlers();
            hs.erase(std::remove(hs.begin(), hs.end(), h), hs.end());
            // 等待在途 dispatch 结束，确保 handler 销毁后不会被调用
            cv().wait(lock, [] { return inFlight() == 0; });
        }

        static void dispatch(OutputPlatformInfo *info) noexcept
        {
            std::vector<OutputHandler *> snapshot;
            {
                std::lock_guard<std::mutex> lock(mutex());
                snapshot = handlers();
                ++inFlight();
            }
            for (OutputHandler *h : snapshot)
            {
                if (h == nullptr)
                    continue;
                // 违反 noexcept 的处理函数会终止进程（std::terminate），这是有意为之——
                // 回调边界错误应显式失败而非静默吞掉
                h->onOutput(info);
            }
            {
                std::lock_guard<std::mutex> lock(mutex());
                --inFlight();
                cv().notify_all();
            }
        }

    private:
        static std::mutex &mutex()
        {
            static std::mutex s_mutex;
            return s_mutex;
        }
        static std::condition_variable &cv()
        {
            static std::condition_variable s_cv;
            return s_cv;
        }
        static int &inFlight()
        {
            static int s_in_flight = 0;
            return s_in_flight;
        }
        static std::vector<OutputHandler *> &handlers()
        {
            static std::vector<OutputHandler *> s_handlers;
            return s_handlers;
        }
    };
}
