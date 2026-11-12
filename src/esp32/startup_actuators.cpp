#include "firmware/startup_actuators.h"

#if defined(CONFIG_IDF_TARGET_ESP32C3)
#include "config.h"

namespace {
constexpr uint8_t PWM_CHANNEL = 0;
constexpr uint32_t PWM_FREQUENCY_HZ = 25000;
constexpr uint8_t PWM_RESOLUTION_BITS = 8;
constexpr uint32_t PWM_MAX_DUTY = (1U << PWM_RESOLUTION_BITS) - 1;
constexpr uint32_t RPM_INTERVAL_MS = 1000;
constexpr uint32_t MILLISECONDS_PER_MINUTE = 60000;
constexpr uint32_t TACH_PULSES_PER_REVOLUTION = 2;
}  // namespace

void StartupActuators::begin(uint32_t now) {
  digitalWrite(Config::FOGGER_ENABLE_PIN, LOW);
  pinMode(Config::FOGGER_ENABLE_PIN, OUTPUT);
  pinMode(Config::FAN_TACH_PIN, INPUT_PULLUP);
  attachInterruptArg(Config::FAN_TACH_PIN, onTachPulse, this, FALLING);
  lastRpmAt_ = now;
  status_.hardwareReady = ledcSetup(PWM_CHANNEL, PWM_FREQUENCY_HZ, PWM_RESOLUTION_BITS) != 0;
  if (status_.hardwareReady) {
    ledcAttachPin(Config::FAN_PWM_PIN, PWM_CHANNEL);
    if (AutomaticLimits::STARTUP_TEST_ENABLED) {
      startup_.begin(now);
    } else {
      startup_.skip();
    }
  } else {
    startup_.abort();
  }
  applyOutputs(now);
}

void IRAM_ATTR StartupActuators::onTachPulse(void* instance) {
  auto& self = *static_cast<StartupActuators*>(instance);
  portENTER_CRITICAL_ISR(&self.tachMux_);
  ++self.tachPulses_;
  portEXIT_CRITICAL_ISR(&self.tachMux_);
}

void StartupActuators::updateRpm(uint32_t now) {
  const uint32_t elapsed = now - lastRpmAt_;
  if (elapsed < RPM_INTERVAL_MS) {
    return;
  }
  portENTER_CRITICAL(&tachMux_);
  const uint32_t pulses = tachPulses_;
  portEXIT_CRITICAL(&tachMux_);
  status_.rpm = static_cast<uint64_t>(pulses - previousPulses_) * MILLISECONDS_PER_MINUTE /
                (TACH_PULSES_PER_REVOLUTION * elapsed);
  status_.rpmValid = true;
  previousPulses_ = pulses;
  lastRpmAt_ = now;
}

void StartupActuators::applyOutputs(uint32_t now, const AutomaticControl* automatic) {
  const ActuatorStatus& command = startup_.status();
  status_.startupActive = command.startupActive;
  status_.startupComplete = command.startupComplete;
  status_.aborted = command.aborted;
  status_.completedPulses = command.completedPulses;
  status_.completedFanPulses = command.completedFanPulses;
  status_.foggerTestActive = command.foggerTestActive;
  status_.fanPercent = status_.hardwareReady ? command.fanPercent : 0;
  status_.foggerOn = status_.hardwareReady && command.foggerOn;
  if (manualTookOver_) {
    status_.startupActive = false;
    status_.foggerTestActive = false;
    status_.fanPercent = status_.hardwareReady ? manual_.fanPercent() : 0;
    status_.foggerOn = status_.hardwareReady && manual_.foggerOn(now);
  }
  if (automatic && automatic->ownsOutputs()) {
    status_.startupActive = false;
    status_.foggerTestActive = false;
    status_.fanPercent = status_.hardwareReady ? automatic->fanPercent() : 0;
    status_.foggerOn = status_.hardwareReady && automatic->foggerOn(now);
  }
  if (!AutomaticLimits::FOGGER_ENABLED) {
    status_.foggerOn = false;
    status_.foggerTestActive = false;
    status_.completedPulses = 0;
  }
  if (status_.hardwareReady && status_.fanPercent != appliedFanPercent_) {
    ledcWrite(PWM_CHANNEL, status_.fanPercent * PWM_MAX_DUTY / 100);
    appliedFanPercent_ = status_.fanPercent;
  }
  if (status_.foggerOn != appliedFoggerOn_) {
    digitalWrite(Config::FOGGER_ENABLE_PIN, status_.foggerOn ? HIGH : LOW);
    appliedFoggerOn_ = status_.foggerOn;
  }
}

void StartupActuators::poll(uint32_t now, bool maintenance, bool networkAvailable,
                            const AutomaticControl* automatic) {
  manual_.poll(now, networkAvailable);
  if (manual_.commanded() || (automatic && automatic->ownsOutputs())) {
    manualTookOver_ = true;
  }
  if (maintenance) {
    manual_.stop();
    manualTookOver_ = true;
    startup_.abort();
  } else if (status_.hardwareReady && !manualTookOver_) {
    startup_.poll(now);
  }
  applyOutputs(now, maintenance ? nullptr : automatic);
  updateRpm(now);
}
#endif
