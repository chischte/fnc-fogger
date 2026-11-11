#include "firmware/network_discovery.h"

#include <ESPmDNS.h>
#include <WiFi.h>

#include "config.h"
#include "firmware/time_utils.h"

namespace {
constexpr uint32_t RETRY_INTERVAL_MS = 10000;
constexpr char SERVICE_NAME[] = "fnc-fogger";
constexpr char SERVICE_PROTOCOL[] = "tcp";
}  // namespace

void NetworkDiscovery::poll(bool connected, uint32_t now) {
  if (!connected) {
    if (started_) {
      MDNS.end();
    }
    started_ = false;
    attempted_ = false;
    return;
  }
  if (started_ || (attempted_ &&
                  !hasElapsed(now, lastAttemptAt_, RETRY_INTERVAL_MS))) {
    return;
  }
  attempted_ = true;
  lastAttemptAt_ = now;

  String deviceId = WiFi.macAddress();
  deviceId.replace(":", "");
  deviceId.toLowerCase();
  const String hostname = "fnc-fogger-" + deviceId.substring(6);
  if (!MDNS.begin(hostname.c_str())) {
    Serial.println("mDNS startup failed; retrying later.");
    return;
  }
  if (!MDNS.addService(SERVICE_NAME, SERVICE_PROTOCOL, Config::HTTP_PORT)) {
    MDNS.end();
    Serial.println("mDNS service registration failed; retrying later.");
    return;
  }
  MDNS.addServiceTxt(SERVICE_NAME, SERVICE_PROTOCOL, "id", deviceId);
  MDNS.addServiceTxt(SERVICE_NAME, SERVICE_PROTOCOL, "path", "/api/current");
  MDNS.addServiceTxt(SERVICE_NAME, SERVICE_PROTOCOL, "firmware",
                     Config::FIRMWARE_VERSION);
  MDNS.addServiceTxt(SERVICE_NAME, SERVICE_PROTOCOL, "hardware", FirmwareIdentity::PROFILE);
  MDNS.addServiceTxt(SERVICE_NAME, SERVICE_PROTOCOL, "build", FirmwareIdentity::BUILD);
  started_ = true;
  Serial.println("mDNS: http://" + hostname + ".local");
}
