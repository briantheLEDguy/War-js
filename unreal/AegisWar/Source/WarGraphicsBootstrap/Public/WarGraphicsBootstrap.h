#pragma once
#include "CoreMinimal.h"
#include "Misc/ConfigCacheIni.h"

namespace WarGraphicsBootstrap
{
    /** In-memory migration/repair only; persistence follows confirmed runtime settings. */
    WARGRAPHICSBOOTSTRAP_API void PrepareConfig(FConfigCacheIni& Config, const FString& Ini, bool bSafe);
}
