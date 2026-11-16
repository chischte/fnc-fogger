#pragma once

#include "firmware/automatic_control.h"

bool seedCyclicMistClock(uint32_t unixSeconds);

// Bridges the monotonic control timer to a persisted UTC start across reboots.
class CyclicMistClock {
 public:
  void begin(AutomaticControl& automatic);
  void poll(AutomaticControl& automatic, uint32_t now);

 private:
  uint32_t savedOrigin_ = 0;
  uint32_t lastSaveAttempt_ = 0;
  bool originSaved_ = false;
};
