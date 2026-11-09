"""Discover measurement lances through their advertised mDNS service."""
import threading

from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf

from .lance_registry import Lance

SERVICE_TYPE = "_fnc-fogger._tcp.local."
DISCOVERY_SECONDS = 3


class LanceListener(ServiceListener):
    def __init__(self):
        self.names = set()
        self.lock = threading.Lock()

    def add_service(self, zeroconf, service_type, name):
        with self.lock:
            self.names.add(name)

    def update_service(self, zeroconf, service_type, name):
        self.add_service(zeroconf, service_type, name)

    def remove_service(self, zeroconf, service_type, name):
        with self.lock:
            self.names.discard(name)


def discover_lances(stop=None):
    stop = stop or threading.Event()
    listener = LanceListener()
    found = {}
    with Zeroconf(ip_version=IPVersion.V4Only) as network:
        browser = ServiceBrowser(network, SERVICE_TYPE, listener)
        try:
            stop.wait(DISCOVERY_SECONDS)
            with listener.lock:
                names = sorted(listener.names)
            for name in names:
                if stop.is_set():
                    break
                info = network.get_service_info(SERVICE_TYPE, name, timeout=1500)
                if info is None or not info.server:
                    continue
                device_id = info.properties.get(b"id", b"").decode("utf-8", errors="replace")
                if len(device_id) == 12 and all(c in "0123456789abcdef" for c in device_id):
                    found[device_id] = Lance(device_id, info.server.rstrip("."), info.port)
        finally:
            browser.cancel()
    return list(found.values())
