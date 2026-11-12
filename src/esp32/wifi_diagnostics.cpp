#include "firmware/wifi_diagnostics.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <string.h>

#include "config.h"
#include "firmware/time_utils.h"
#include "wifi-credentials.h"

namespace {
constexpr uint32_t REPORT_INTERVAL_MS = 10000;
constexpr size_t SERIAL_BYTES_PER_POLL = 64;
constexpr uint32_t SCAN_DISCONNECT_DELAY_MS = 200;
constexpr uint32_t SCAN_CHANNEL_TIME_MS = 150;
constexpr uint32_t POWER_RETRY_INTERVAL_MS = 1000;
struct PowerLevel {
  const char* label;
  int8_t quarterDbm;
};
constexpr PowerLevel POWER_LEVELS[] = {
    {"2", 8}, {"5", 20}, {"7", 28}, {"8.5", 34}, {"11", 44},
    {"13", 52}, {"14", 56}, {"15", 60}, {"16.5", 66}, {"18", 72}, {"20", 80}};

const char* statusName(uint8_t status) {
  switch (status) {
    case WL_IDLE_STATUS: return "idle";
    case WL_NO_SSID_AVAIL: return "network_not_found";
    case WL_SCAN_COMPLETED: return "scan_complete";
    case WL_CONNECTED: return "connected";
    case WL_CONNECT_FAILED: return "connect_failed";
    case WL_CONNECTION_LOST: return "connection_lost";
    case WL_DISCONNECTED: return "disconnected";
    default: return "unknown";
  }
}

const char* reasonName(uint8_t reason) {
  switch (reason) {
    case 0: return "none_recorded";
    case WIFI_REASON_NO_AP_FOUND: return "access_point_not_found";
    case WIFI_REASON_AUTH_FAIL: return "authentication_failed";
    case WIFI_REASON_AUTH_EXPIRE: return "authentication_expired";
    case WIFI_REASON_ASSOC_FAIL: return "association_failed";
    case WIFI_REASON_BEACON_TIMEOUT: return "beacon_timeout";
    case WIFI_REASON_HANDSHAKE_TIMEOUT:
    case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
    case WIFI_REASON_GROUP_KEY_UPDATE_TIMEOUT: return "handshake_timeout";
    default: return "other";
  }
}
}  // namespace

void WifiDiagnostics::begin() {
  WiFi.onEvent([this](WiFiEvent_t, WiFiEventInfo_t info) {
    disconnectReason_.store(info.wifi_sta_disconnected.reason);
  }, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
}

void WifiDiagnostics::poll(uint32_t now) {
  applyConfiguredPower(now);
  readCommands(now);
  pollScan(now);
  const uint8_t status = WiFi.status();
  const uint8_t reason = disconnectReason_.load();
  if (status == reportedStatus_ && reason == reportedReason_ &&
      !hasElapsed(now, lastReportAt_, REPORT_INTERVAL_MS)) {
    return;
  }
  reportedStatus_ = status;
  reportedReason_ = reason;
  lastReportAt_ = now;
  report(status, reason);
}

bool WifiDiagnostics::scanActive() const {
  return scanState_ != ScanState::idle;
}

void WifiDiagnostics::readCommands(uint32_t now) {
  for (size_t bytes = 0; bytes < SERIAL_BYTES_PER_POLL && Serial.available(); ++bytes) {
    const int value = Serial.read();
    if (value < 0) return;
    const char character = static_cast<char>(value);
    if (character == '\r' || character == '\n') {
      if (commandOverflow_) {
        Serial.println("[wifi] USB command too long; ignored");
      } else if (commandLength_ > 0) {
        command_[commandLength_] = '\0';
        executeCommand(now);
      }
      commandLength_ = 0;
      commandOverflow_ = false;
    } else if (commandLength_ + 1 < sizeof(command_)) {
      command_[commandLength_++] = character;
    } else {
      commandOverflow_ = true;
    }
  }
}

void WifiDiagnostics::executeCommand(uint32_t now) {
  if (strcmp(command_, "wifi") == 0 || strcmp(command_, "wifi status") == 0) {
    report(WiFi.status(), disconnectReason_.load());
  } else if (strcmp(command_, "wifi scan") == 0) {
    requestScan(now);
  } else if (strncmp(command_, "wifi power ", 11) == 0) {
    setPower(command_ + 11);
  } else if (strcmp(command_, "wifi reconnect") == 0) {
    if (!scanActive()) Serial.printf("[wifi] reconnect requested=%u\n", WiFi.reconnect());
  } else {
    Serial.println("[wifi] commands: wifi status | wifi scan | wifi reconnect | wifi power default/2/5/7/8.5/11/13/14/15/16.5/18/20");
  }
}

void WifiDiagnostics::requestScan(uint32_t now) {
  if (scanActive() || WiFi.status() == WL_CONNECTED) {
    Serial.println("[wifi scan] refused: scan active or Wi-Fi already connected");
    return;
  }
  originalAutoReconnect_ = WiFi.getAutoReconnect();
  WiFi.setAutoReconnect(false);
  if (!WiFi.disconnect(false, false)) {
    WiFi.setAutoReconnect(originalAutoReconnect_);
    Serial.println("[wifi scan] could not pause connection attempt");
    return;
  }
  scanState_ = ScanState::waiting;
  scanRequestedAt_ = now;
  Serial.println("[wifi scan] starting targeted scan; credentials retained");
}

void WifiDiagnostics::pollScan(uint32_t now) {
  if (scanState_ == ScanState::idle) return;
  if (scanState_ == ScanState::waiting) {
    if (!hasElapsed(now, scanRequestedAt_, SCAN_DISCONNECT_DELAY_MS)) return;
    const int16_t result = WiFi.scanNetworks(true, false, false, SCAN_CHANNEL_TIME_MS,
                                            0, WIFI_SSID);
    if (result == WIFI_SCAN_RUNNING) {
      scanState_ = ScanState::running;
    } else {
      finishScan(result);
    }
    return;
  }
  const int16_t result = WiFi.scanComplete();
  if (result != WIFI_SCAN_RUNNING) finishScan(result);
}

void WifiDiagnostics::finishScan(int16_t count) {
  if (count < 0) {
    Serial.println("[wifi scan] failed; normal connection retries resumed");
  } else {
    Serial.printf("[wifi scan] matching access points=%d\n", count);
    for (int16_t index = 0; index < count; ++index) {
      if (WiFi.SSID(index) != WIFI_SSID) continue;
      Serial.printf("[wifi scan] target: rssi=%ld dBm, channel=%ld, auth=%u, bssid=%s\n",
                    static_cast<long>(WiFi.RSSI(index)), static_cast<long>(WiFi.channel(index)),
                    static_cast<unsigned>(WiFi.encryptionType(index)),
                    WiFi.BSSIDstr(index).c_str());
    }
  }
  WiFi.scanDelete();
  WiFi.setAutoReconnect(originalAutoReconnect_);
  scanState_ = ScanState::idle;
}

void WifiDiagnostics::setPower(const char* value) {
  int8_t requested = Config::WIFI_TX_POWER_QDBM;
  bool recognized = strcmp(value, "default") == 0 || strcmp(value, "low") == 0;
  for (const auto& level : POWER_LEVELS) {
    if (strcmp(value, level.label) != 0) continue;
    requested = level.quarterDbm;
    recognized = true;
    break;
  }
  if (!recognized) {
    Serial.println("[wifi] unsupported TX power; unchanged");
    return;
  }
  const bool applied = WiFi.setTxPower(static_cast<wifi_power_t>(requested));
  Serial.printf("[wifi] temporary TX power applied=%u, tx_power_qdbm=%d; restart restores firmware default\n",
                applied, static_cast<int>(WiFi.getTxPower()));
}

void WifiDiagnostics::applyConfiguredPower(uint32_t now) {
  if (configuredPowerApplied_ ||
      !hasElapsed(now, lastPowerAttemptAt_, POWER_RETRY_INTERVAL_MS)) return;
  lastPowerAttemptAt_ = now;
  configuredPowerApplied_ = WiFi.setTxPower(
      static_cast<wifi_power_t>(Config::WIFI_TX_POWER_QDBM));
  if (configuredPowerApplied_) {
    Serial.printf("[wifi] firmware TX power applied: tx_power_qdbm=%d\n",
                  static_cast<int>(WiFi.getTxPower()));
  }
}

void WifiDiagnostics::report(uint8_t status, uint8_t reason) {
  Serial.printf("[wifi] status=%s (%u), last_disconnect=%s (%u)",
                statusName(status), static_cast<unsigned>(status),
                reasonName(reason), static_cast<unsigned>(reason));
  Serial.printf(", tx_power_qdbm=%d", static_cast<int>(WiFi.getTxPower()));
  if (status == WL_CONNECTED) {
    Serial.printf(", ip=%s, rssi=%ld dBm, channel=%ld",
                  WiFi.localIP().toString().c_str(),
                  static_cast<long>(WiFi.RSSI()), static_cast<long>(WiFi.channel()));
    wifi_ap_record_t accessPoint = {};
    if (esp_wifi_sta_get_ap_info(&accessPoint) == ESP_OK) {
      Serial.printf(", auth=%u", static_cast<unsigned>(accessPoint.authmode));
    }
  }
  Serial.println();
}
