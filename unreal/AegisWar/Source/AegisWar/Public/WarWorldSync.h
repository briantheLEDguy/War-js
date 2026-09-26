#pragma once
#include "CoreMinimal.h"
#include "WarWorldEditHistory.h"

namespace WarWorldSync
{
    // Validate a remote snapshot against the installed native baseline before changing actors.
    AEGISWAR_API bool PreparePull(const FString& Response, const FString& Map, int32 ExpectedRevision,
        FWarWorldEditHistory& Next, int32& RemoteRevision, FString& Error);
}
