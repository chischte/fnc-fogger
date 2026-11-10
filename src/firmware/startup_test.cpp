#include "firmware/startup_test.h"

void StartupTest::begin(uint32_t now) {
  phase_ = Phase::waiting;
  phaseStartedAt_ = now;
  status_ = ActuatorStatus{};
  status_.startupActive = true;
}

void StartupTest::pollFogger(uint32_t now) {
  const uint32_t duration = status_.foggerOn ? FOGGER_PULSE_MS : FOGGER_PAUSE_MS;
  if (now - foggerPhaseStartedAt_ < duration) {
    return;
  }
  if (status_.foggerOn) {
    ++status_.completedPulses;
  }
  status_.foggerOn = !status_.foggerOn;
  foggerPhaseStartedAt_ = now;
}

void StartupTest::poll(uint32_t now) {
  const uint32_t elapsed = now - phaseStartedAt_;
  if (phase_ == Phase::waiting && elapsed >= START_DELAY_MS) {
    phase_ = Phase::running;
    phaseStartedAt_ = now;
    foggerPhaseStartedAt_ = now;
    status_.fanPercent = 100;
    status_.foggerOn = true;
    status_.foggerTestActive = true;
    return;
  }
  if (phase_ == Phase::running) {
    // The common deadline stops both outputs even if polling was delayed.
    if (elapsed < FAN_PULSE_MS) {
      pollFogger(now);
      return;
    }
    if (status_.foggerOn) {
      ++status_.completedPulses;
    }
    status_.fanPercent = 0;
    status_.foggerOn = false;
    status_.foggerTestActive = false;
    status_.completedFanPulses = 1;
    phase_ = Phase::pause;
    phaseStartedAt_ = now;
    return;
  }
  if (phase_ == Phase::pause && elapsed >= FAN_PAUSE_MS) {
    phase_ = Phase::complete;
    status_.startupActive = false;
    status_.startupComplete = true;
  }
}

void StartupTest::abort() {
  phase_ = Phase::aborted;
  status_.startupActive = false;
  status_.foggerTestActive = false;
  status_.aborted = true;
  status_.foggerOn = false;
  status_.fanPercent = 100;
}
