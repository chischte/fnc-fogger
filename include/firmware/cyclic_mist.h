#pragma once

#include <stdint.h>

struct CyclicMistSettings {
  bool enabled = false;
  uint8_t mistMinutes = 0;
  uint8_t pauseMinutes = 10;

  bool valid() const {
    return mistMinutes <= 10 && (!enabled || mistMinutes > 0) && pauseMinutes >= 10 &&
           pauseMinutes <= 60 && pauseMinutes % 5 == 0;
  }
};

// Device-side wall-clock schedule; no networking, GPIO or PI dependencies.
class CyclicMist {
 public:
  static constexpr uint32_t MINUTE_MS = 60000;

  bool configure(const CyclicMistSettings& settings, uint32_t now) {
    if (!settings.valid()) return false;
    const bool changed = settings.enabled != settings_.enabled ||
        settings.mistMinutes != settings_.mistMinutes ||
        settings.pauseMinutes != settings_.pauseMinutes;
    settings_ = settings;
    if (changed) startedAt_ = now;
    poll(now);
    return true;
  }

  void poll(uint32_t now) {
    if (!settings_.enabled) {
      misting_ = false;
      return;
    }
    const uint32_t period = durationMs() + settings_.pauseMinutes * MINUTE_MS;
    const uint32_t elapsed = now - startedAt_;
    // Advance the origin regularly so millis() rollover preserves the phase.
    startedAt_ += (elapsed / period) * period;
    misting_ = now - startedAt_ < durationMs();
  }

  const CyclicMistSettings& settings() const { return settings_; }
  bool misting() const { return misting_; }
  uint32_t remainingMs(uint32_t now) const {
    if (!settings_.enabled) return 0;
    const uint32_t period = durationMs() + settings_.pauseMinutes * MINUTE_MS;
    const uint32_t elapsed = (now - startedAt_) % period;
    return elapsed < durationMs() ? durationMs() - elapsed : period - elapsed;
  }

 private:
  uint32_t durationMs() const { return settings_.mistMinutes * MINUTE_MS; }
  CyclicMistSettings settings_;
  uint32_t startedAt_ = 0;
  bool misting_ = false;
};
