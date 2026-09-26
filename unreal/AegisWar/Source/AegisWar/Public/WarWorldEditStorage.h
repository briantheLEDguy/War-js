#pragma once
#include "CoreMinimal.h"

namespace WarWorldEditStorage
{
    AEGISWAR_API bool Read(const FString& Path, FString& Contents, FString& Error);
    // Compare the observed publication under a writer lock, then atomically replace it.
    AEGISWAR_API bool Publish(const FString& Path, const FString& Observed, const FString& Contents, FString& Error);
}
