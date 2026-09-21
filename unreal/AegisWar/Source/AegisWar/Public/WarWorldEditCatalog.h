#pragma once
#include "CoreMinimal.h"
#include "WarWorldEditHistory.h"

struct FWarWorldEditCatalogEntry
{
    FName TemplateId;
    FString Label;
    FString SourceIdentity;
};

namespace WarWorldEditCatalog
{
    AEGISWAR_API TArray<FWarWorldEditCatalogEntry> Build(const TArray<FWarWorldEditObject>& Baseline);
    AEGISWAR_API TArray<FWarWorldEditCatalogEntry> Filter(const TArray<FWarWorldEditCatalogEntry>& Entries, const FString& Query);
}
