#pragma once
#include "CoreMinimal.h"
class FWarWorldEditHistory;

namespace WarCapitalReplacements
{
    /** Admission comes from installed authoring data, never from a GM draft. */
    bool RegisterReviewed(FWarWorldEditHistory& History, FString& Error);
}
