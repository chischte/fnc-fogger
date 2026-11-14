#pragma once

struct PiTerms {
  float p = 0;
  float i = 0;
  float sum = 0;
};

// Bound I to 0..maximum and stop accumulation into upper output saturation.
class PiController {
 public:
  PiController(float gain, float integralSeconds) : gain_(gain), integralSeconds_(integralSeconds) {}
  void reset() { terms_ = {}; }
  void restoreIntegral(float integral, float maximum) {
    terms_.i = integral;
    terms_.sum = terms_.p + integral;
    if (terms_.sum < 0) terms_.sum = 0;
    if (terms_.sum > maximum) terms_.sum = maximum;
  }
  void resetIntegral(float maximum) {
    terms_.i = 0;
    terms_.sum = terms_.p < 0 ? 0 : terms_.p > maximum ? maximum : terms_.p;
  }
  float update(float error, float elapsedSeconds, float minimum, float maximum);
  const PiTerms& terms() const { return terms_; }

 private:
  float gain_;
  float integralSeconds_;
  PiTerms terms_;
};
