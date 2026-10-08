#pragma once
#include "CoreMinimal.h"
#include "HAL/PlatformProcess.h"
#include "Modules/ModuleManager.h"

namespace WarProofBinary
{
// Bind the code actually loaded: a module in Editor, the executable in monolithic Game.
inline FString LoadedAegisWar()
{
#if IS_MONOLITHIC
    return FPlatformProcess::ExecutablePath();
#else
    return FModuleManager::Get().GetModuleFilename(TEXT("AegisWar"));
#endif
}
}
