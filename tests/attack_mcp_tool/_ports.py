"""端口重绑探针（AC-05 / U-2）：以组件自身的绑定语义判定「可重绑」。

为什么不用裸 `socket.bind` 判定：POSIX 上组件设置了 `SO_REUSEADDR`，可在
`TIME_WAIT` 期间重绑；裸 socket 未设该选项，内核仍持有 `TIME_WAIT` 条目时会报
`EADDRINUSE`，从而把「组件可重绑」误判为「端口未释放」。该误判已在 CI（Linux）
实测出现：50 次请求后 `stop()`，裸探针 2 s 内始终失败，组件自身重绑则即时成功。

因此探针复用 `PoisonedMcpServer` 的绑定路径，判据与产品一致。
"""
import time

from tools.attack_mcp_tool import poison


def rebind_within(port, window=2.0, interval=0.05):
    """在 `window` 秒内以组件语义重绑 `port`，返回耗时；超窗抛 AssertionError。"""
    started = time.perf_counter()
    deadline = started + window
    while True:
        probe = poison.PoisonedMcpServer(port=port)
        try:
            probe.start()
            return time.perf_counter() - started
        except OSError:
            if time.perf_counter() > deadline:
                raise AssertionError("端口 %d 未在 %.1fs 内可重绑" % (port, window))
            time.sleep(interval)
        finally:
            probe.stop()
