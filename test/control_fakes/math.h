#pragma once
#define NAN (__builtin_nanf(""))
inline bool isfinite(float value) { return __builtin_isfinite(value); }
