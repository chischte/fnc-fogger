#include "firmware/cyclic_mist_clock.h"

#include <Arduino.h>
#include <time.h>
#include <sys/time.h>
#include "firmware/cyclic_mist_store.h"

namespace {
constexpr time_t MIN_VALID_UNIX_TIME = 1704067200; // 2024-01-01 UTC
constexpr uint32_t SAVE_RETRY_MS = 1000;
constexpr uint32_t MS_PER_SECOND = 1000;
}

bool seedCyclicMistClock(uint32_t unixSeconds) {
  if (unixSeconds < MIN_VALID_UNIX_TIME) return false;
  if (time(nullptr) >= MIN_VALID_UNIX_TIME) return true;
  const timeval value = {static_cast<time_t>(unixSeconds), 0};
  return settimeofday(&value, nullptr) == 0;
}

void CyclicMistClock::begin(AutomaticControl& automatic) {
  automatic.waitForCyclicMistClock();
  configTime(0, 0, "pool.ntp.org", "time.cloudflare.com");
}

void CyclicMistClock::poll(AutomaticControl& automatic, uint32_t now) {
  const time_t utc = time(nullptr);
  if (utc < MIN_VALID_UNIX_TIME) return;
  const CyclicMist& mist = automatic.cyclicMist();
  if (mist.waitingForClock()) {
    uint32_t lastStart = 0;
    const bool known = loadCyclicMistStart(lastStart) && lastStart <= utc;
    const uint32_t elapsedSeconds = known ? static_cast<uint32_t>(utc - lastStart) : 0;
    const uint32_t periodSeconds = mist.periodMs() / MS_PER_SECOND;
    automatic.restoreCyclicMistPhase(now,
        min(elapsedSeconds, periodSeconds) * MS_PER_SECOND);
    originSaved_ = false;
  }
  if (!mist.settings().enabled) return;
  if (originSaved_ && savedOrigin_ == mist.startedAt()) return;
  if (now - lastSaveAttempt_ < SAVE_RETRY_MS) return;
  lastSaveAttempt_ = now;
  const uint32_t start = static_cast<uint32_t>(utc) - (now - mist.startedAt()) / MS_PER_SECOND;
  if (!saveCyclicMistStart(start)) {
    Serial.println("Cyclic mist start could not be saved; retry pending");
    return;
  }
  savedOrigin_ = mist.startedAt();
  originSaved_ = true;
}
