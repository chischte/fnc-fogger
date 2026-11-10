#pragma once

#ifndef FNC_BUILD_ID
#define FNC_BUILD_ID "development"
#endif

#if defined(CONFIG_IDF_TARGET_ESP32C3)
#define FNC_HARDWARE_PROFILE "esp32c3_supermini"
#define FNC_FIRMWARE_VERSION "3.4.1-esp32c3"
#elif defined(ARDUINO_ARCH_ESP32)
#define FNC_HARDWARE_PROFILE "esp32s3"
#define FNC_FIRMWARE_VERSION "3.2.0-esp32s3"
#else
#define FNC_HARDWARE_PROFILE "portenta_h7_m7"
#define FNC_FIRMWARE_VERSION "3.1.0-portenta"
#endif

namespace FirmwareIdentity {
constexpr char PROFILE[] = FNC_HARDWARE_PROFILE;
constexpr char BUILD[] = FNC_BUILD_ID;
constexpr char VERSION[] = FNC_FIRMWARE_VERSION;
// Embedded in the image and checked by the upload client and device.
constexpr char PROFILE_MARKER[] = "FNC_FW|" FNC_HARDWARE_PROFILE "|";
constexpr char METADATA[] = "FNC_FW|" FNC_HARDWARE_PROFILE "|"
                           FNC_FIRMWARE_VERSION "|" FNC_BUILD_ID "|END";
}  // namespace FirmwareIdentity
