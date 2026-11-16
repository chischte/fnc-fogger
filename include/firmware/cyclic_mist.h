#pragma once

#include <stdint.h>

struct CyclicMistSettings {
  bool enabled = false;
  uint8_t mistMinutes = 0;
  uint8_t pauseMinutes = 10;

  bool valid() const {
    return mistMinutes <= 10 && (!enabled || mistMinutes > 0) && pauseMinutes >= 10 &&
           pauseMinutes <= 60;
  }
};

// Device-side wall-clock schedule; no networking, GPIO or PI dependencies.
class CyclicMist {
 public:
  static constexpr uint32_t MINUTE_MS = 60000;
  static constexpr uint32_t SETTLING_MS = MINUTE_MS;

  bool configure(const CyclicMistSettings& settings, uint32_t now) {
    if (!settings.valid()) return false;
    settings_ = settings;
    if (!hasOrigin_) {
      startedAt_ = now;
      hasOrigin_ = true;
    }
    poll(now);
    return true;
  }

  void poll(uint32_t now) {
    if (!settings_.enabled || waitingForClock_) {
      misting_ = false;
      settling_ = false;
      return;
    }
    const uint32_t period = durationMs() + settings_.pauseMinutes * MINUTE_MS;
    const uint32_t elapsed = now - startedAt_;
    // Advance the origin regularly so millis() rollover preserves the phase.
    startedAt_ += (elapsed / period) * period;
    if (elapsed >= period) skipCurrentMist_ = false;
    misting_ = !skipCurrentMist_ && now - startedAt_ < durationMs();
    settling_ = !skipCurrentMist_ && now - startedAt_ >= durationMs() &&
        now - startedAt_ < durationMs() + SETTLING_MS;
  }

  void waitForClock() { waitingForClock_ = true; misting_ = settling_ = false; }
  bool waitingForClock() const { return waitingForClock_; }
  uint32_t startedAt() const { return startedAt_; }
  uint32_t periodMs() const { return durationMs() + settings_.pauseMinutes * MINUTE_MS; }
  void restorePhase(uint32_t now, uint32_t elapsedMs) {
    const bool overdue = elapsedMs >= periodMs();
    startedAt_ = overdue ? now : now - elapsedMs;
    hasOrigin_ = true;
    waitingForClock_ = false;
    // A restart never repeats or extends a partially completed mist phase.
    skipCurrentMist_ = !overdue;
    poll(now);
  }

  const CyclicMistSettings& settings() const { return settings_; }
  bool misting() const { return misting_; }
  bool settling() const { return settling_; }
  uint32_t remainingMs(uint32_t now) const {
    if (!settings_.enabled || waitingForClock_) return 0;
    const uint32_t period = durationMs() + settings_.pauseMinutes * MINUTE_MS;
    const uint32_t elapsed = (now - startedAt_) % period;
    if (settling_) return durationMs() + SETTLING_MS - elapsed;
    return elapsed < durationMs() && !skipCurrentMist_ ? durationMs() - elapsed : period - elapsed;
  }

 private:
  uint32_t durationMs() const { return settings_.mistMinutes * MINUTE_MS; }
  CyclicMistSettings settings_;
  uint32_t startedAt_ = 0;
  bool misting_ = false;
  bool settling_ = false;
  bool hasOrigin_ = false;
  bool waitingForClock_ = false;
  bool skipCurrentMist_ = false;
};
