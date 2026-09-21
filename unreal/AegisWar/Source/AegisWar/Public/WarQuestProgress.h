#pragma once
#include "CoreMinimal.h"
#include "WarQuestProgress.generated.h"

USTRUCT(BlueprintType)
struct AEGISWAR_API FWarQuestCounter
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Id;
    UPROPERTY(BlueprintReadOnly) int32 Count = 0;
};

USTRUCT(BlueprintType)
struct AEGISWAR_API FWarQuestProgress
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Id;
    UPROPERTY(BlueprintReadOnly) FName Status = TEXT("active");
    UPROPERTY(BlueprintReadOnly) TArray<FWarQuestCounter> Counters;
    int32 GetCount(FName Objective) const
    {
        const auto* Found = Counters.FindByPredicate([&](const auto& Row) { return Row.Id == Objective; });
        return Found ? Found->Count : 0;
    }
    void SetCount(FName Objective, int32 Count)
    {
        auto* Found = Counters.FindByPredicate([&](const auto& Row) { return Row.Id == Objective; });
        if (Found) Found->Count = Count;
        else { FWarQuestCounter Row; Row.Id = Objective; Row.Count = Count; Counters.Add(Row); }
    }
};
