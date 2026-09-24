#pragma once
#include "CoreMinimal.h"
#include "WarProgressionRules.generated.h"

USTRUCT(BlueprintType)
struct AEGISWAR_API FWarCharacterProgression
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Level = 1;
    UPROPERTY(BlueprintReadOnly) int64 Xp = 0;
    UPROPERTY(BlueprintReadOnly) int64 Gold = 0;
    UPROPERTY(BlueprintReadOnly) int32 BaseStrength = 10;
    UPROPERTY(BlueprintReadOnly) int32 MaxHealth = 100;
    UPROPERTY(BlueprintReadOnly) int32 MaxMana = 100;
};
namespace WarProgression
{
    constexpr int32 MaxGmLevel = 45;
    // Adjust only level-derived growth; retain other stat offsets and currency.
    AEGISWAR_API bool SetGmLevel(const FWarCharacterProgression& Current, int32 Level,
        FWarCharacterProgression& Next, FString& Error);
    AEGISWAR_API int64 XpForLevel(int32 Level);
    AEGISWAR_API bool Award(const FWarCharacterProgression& Current, int32 Xp, int32 Gold,
        FWarCharacterProgression& Next, FString& Error);
}
