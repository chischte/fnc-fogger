#include "firmware/pi_controller.h"

float PiController::update(float error, float elapsedSeconds, float minimum, float maximum) {
  terms_.p = gain_ * error;
  float integral = terms_.i + gain_ * error * elapsedSeconds / integralSeconds_;
  if (integral > maximum) integral = maximum;
  if (integral < -maximum) integral = -maximum;
  const float candidate = terms_.p + integral;
  if (!((candidate > maximum && error > 0) || (candidate < minimum && error < 0))) {
    terms_.i = integral;
  }
  terms_.sum = terms_.p + terms_.i;
  if (terms_.sum < minimum) terms_.sum = minimum;
  if (terms_.sum > maximum) terms_.sum = maximum;
  return terms_.sum;
}
