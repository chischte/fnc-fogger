#pragma once
#include <stddef.h>
#include <stdint.h>

class Preferences {
 public:
  inline static uint8_t bytes[32] = {};
  inline static size_t length = 0;
  inline static unsigned writes = 0;
  inline static bool failOpen = false;
  inline static bool failWrite = false;

  bool begin(const char*, bool) { return !failOpen; }
  void end() {}
  size_t getBytesLength(const char*) { return length; }
  size_t getBytes(const char*, void* destination, size_t size) {
    if (size != length) return 0;
    auto* output = static_cast<uint8_t*>(destination);
    for (size_t index = 0; index < size; ++index) output[index] = bytes[index];
    return size;
  }
  size_t putBytes(const char*, const void* source, size_t size) {
    if (failWrite || size > sizeof(bytes)) return 0;
    const auto* input = static_cast<const uint8_t*>(source);
    for (size_t index = 0; index < size; ++index) bytes[index] = input[index];
    length = size;
    ++writes;
    return size;
  }
};
