#include "WarCitadelNavigationFilter.h"

void UWarCitadelNavigationFilter::InitializeFilter(const ANavigationData& NavData,
    const UObject* Querier, FNavigationQueryFilter& Filter) const
{
    Super::InitializeFilter(NavData, Querier, Filter);
    Filter.SetMaxSearchNodes(SearchNodeBudget);
}
