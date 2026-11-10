#pragma once
#include <stddef.h>
#include <stdint.h>

#define IRAM_ATTR
#define portMUX_INITIALIZER_UNLOCKED 0
using portMUX_TYPE = int;
inline void portENTER_CRITICAL(portMUX_TYPE*) {}
inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
inline void portENTER_CRITICAL_ISR(portMUX_TYPE*) {}
inline void portEXIT_CRITICAL_ISR(portMUX_TYPE*) {}
constexpr int LOW = 0, HIGH = 1, OUTPUT = 2, INPUT_PULLUP = 3, FALLING = 4;
inline int pinValues[32] = {};
inline int pinModes[32] = {};
inline bool pwmAvailable = true;
inline uint32_t pwmDuty = 0;
inline int pwmPin = -1;
inline void (*tachHandler)(void*) = nullptr;
inline void* tachInstance = nullptr;
inline void digitalWrite(int pin, int value) { pinValues[pin] = value; }
inline void pinMode(int pin, int mode) { pinModes[pin] = mode; }
inline uint32_t ledcSetup(uint8_t, uint32_t frequency, uint8_t) { return pwmAvailable ? frequency : 0; }
inline void ledcAttachPin(int pin, uint8_t) { pwmPin = pin; }
inline void ledcWrite(uint8_t, uint32_t duty) { pwmDuty = duty; }
inline void attachInterruptArg(int, void (*handler)(void*), void* instance, int) {
  tachHandler = handler;
  tachInstance = instance;
}
