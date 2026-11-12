#pragma once

struct PiTerms {
  float p = 0;
  float i = 0;
  float sum = 0;
};

// Conditional integration prevents windup at either actuator limit.
class PiController {
 public:
  PiController(float gain, float integralSeconds) : gain_(gain), integralSeconds_(integralSeconds) {}
  void reset() { terms_ = {}; }
  float update(float error, float elapsedSeconds, float minimum, float maximum);
  const PiTerms& terms() const { return terms_; }

 private:
  float gain_;
  float integralSeconds_;
  PiTerms terms_;
};
