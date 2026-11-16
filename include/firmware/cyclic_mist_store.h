#pragma once

#include "firmware/cyclic_mist.h"

bool loadCyclicMistSettings(CyclicMistSettings& settings);
bool saveCyclicMistSettings(const CyclicMistSettings& settings);
bool loadCyclicMistStart(uint32_t& unixSeconds);
bool saveCyclicMistStart(uint32_t unixSeconds);
