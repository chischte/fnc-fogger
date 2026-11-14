#include "firmware/pi_memory.h"
#include "firmware/automatic_control.h"
#include <Preferences.h>

namespace {
constexpr char STORAGE_NAMESPACE[] = "pi-memory";
constexpr char STORAGE_KEY[] = "integrals";
constexpr uint32_t STORAGE_VERSION = 1;
struct StoredMemory {
  uint32_t version;
  PiMemory values;
};
bool valid(const PiMemory& memory) {
  return memory.co2 >= 0 && memory.co2 <= AutomaticLimits::FAN_MAX_PERCENT &&
      memory.humidity >= 0 && memory.humidity <= AutomaticLimits::FOGGER_MAX_PERCENT;
}
}

bool loadPiMemory(PiMemory& memory) {
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, true)) return false;
  StoredMemory stored;
  const bool read = storage.getBytesLength(STORAGE_KEY) == sizeof(stored) &&
      storage.getBytes(STORAGE_KEY, &stored, sizeof(stored)) == sizeof(stored);
  storage.end();
  if (!read || stored.version != STORAGE_VERSION || !valid(stored.values)) return false;
  memory = stored.values;
  return true;
}

bool savePiMemory(const PiMemory& memory) {
  if (!valid(memory)) return false;
  PiMemory previous;
  if (loadPiMemory(previous) && memory == previous) return true;
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  const StoredMemory stored = {STORAGE_VERSION, memory};
  const bool saved = storage.putBytes(STORAGE_KEY, &stored, sizeof(stored)) == sizeof(stored);
  storage.end();
  return saved;
}
