#pragma once
#include "CoreMinimal.h"
#include "NavFilters/NavigationQueryFilter.h"
#include "WarCitadelNavigationFilter.generated.h"

/** Bounded search for the expanded v2 citadel; area and collision rules stay inherited. */
UCLASS()
class AEGISWAR_API UWarCitadelNavigationFilter : public UNavigationQueryFilter
{
    GENERATED_BODY()
public:
    static constexpr int32 SearchNodeBudget = 8192;
protected:
    virtual void InitializeFilter(const ANavigationData& NavData, const UObject* Querier,
        FNavigationQueryFilter& Filter) const override;
};
