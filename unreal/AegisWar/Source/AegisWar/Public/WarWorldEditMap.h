#pragma once
#include "CoreMinimal.h"

namespace WarWorldEditMap
{
    // Map selection never grants authority; the caller still enforces standalone GM access.
    inline bool IsSupported(const FString& Package, const FString& SelectedMap)
    {
        return Package == TEXT("/Game/Capitals/aegis_capital/AegisCapital_Workbench")
            || Package == TEXT("/Game/Capitals/kit_pilot/AegisCapital_Workbench")
            || Package == TEXT("/Game/Capitals/crownward/AegisCapital_Workbench")
            || (SelectedMap.StartsWith(TEXT("/Game/Capitals/crownward/")) && Package == SelectedMap);
    }
}
