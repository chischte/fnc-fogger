#pragma once
#include <stdint.h>
class String;

enum class HumidityReferenceKind : uint32_t { assumedSaturation = 0, runningCalibration = 1 };

struct HumidityReference {
  uint32_t version = 2;
  uint32_t revision = 0;
  float shtRaw = 0;
  float scdRaw = 0;
  float shtOffset = 1;
  float scdOffset = 0;
  uint32_t durationMs = 0;
  HumidityReferenceKind kind = HumidityReferenceKind::assumedSaturation;
};

bool loadHumidityReference(HumidityReference& reference);
bool saveHumidityReference(const HumidityReference& reference);

class HumidityCalibration {
 public:
  static constexpr uint32_t STABILITY_MS = 3 * 60 * 1000;
  static constexpr float MINIMUM_RISE_RH = 0.1f;
  static constexpr uint8_t FAN_PERCENT = 30;
  static constexpr uint8_t FOGGER_PERCENT = 100;
  void begin() { loadHumidityReference(reference_); }
  bool capture(float shtRaw, float scdRaw, uint32_t durationMs = 0);
  bool runningCalibration(uint32_t now, float shtRaw, bool shtValid, float scdRaw, bool scdValid);
  void checkpointRunning(uint32_t now, bool force = false);
  bool pendingSave() const { return pendingSave_; }
  bool saveFailed() const { return saveFailed_; }
  void start(uint32_t now);
  void observeHumidity(uint32_t now, float humidity, bool valid);
  uint32_t elapsed(uint32_t now) const { return now - startedAt_; }
  void cancel(const char* reason) { running_ = false; status_ = reason; }
  bool running() const { return running_; }
  bool due(uint32_t now) const { return running_ && hasHumidity_ && now - lastRiseAt_ >= STABILITY_MS; }
  uint32_t remaining(uint32_t now) const {
    if (!running_ || due(now)) return 0;
    return hasHumidity_ ? STABILITY_MS - (now - lastRiseAt_) : STABILITY_MS;
  }
  const HumidityReference& reference() const { return reference_; }
  String json(uint32_t now) const;
 private:
  HumidityReference reference_;
  uint32_t startedAt_ = 0;
  uint32_t lastRiseAt_ = 0;
  float riseReferenceRh_ = 0;
  bool hasHumidity_ = false;
  bool running_ = false;
  bool pendingSave_ = false;
  bool saveFailed_ = false;
  bool saveAttempted_ = false;
  uint32_t lastSaveAttemptAt_ = 0;
  const char* status_ = "idle";
};
