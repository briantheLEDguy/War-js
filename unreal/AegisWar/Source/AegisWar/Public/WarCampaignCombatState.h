#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
class AActor;
class UWorld;
class UAbilitySystemComponent;

/** Pure character custody values. Unknown native effects and unresolved identities remain held. */
namespace WarCampaignCombatState
{
    AEGISWAR_API int64 UnixMs();
    AEGISWAR_API bool ValidKey(const FString& Key, bool AllowEmpty = false);
    AEGISWAR_API bool KeyFor(const AActor* Actor, FString& Key, FString& Error);
    AEGISWAR_API AActor* Resolve(UWorld* World, const FString& Key);
    AEGISWAR_API bool Number(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, double& Value, double Minimum = 0, double Maximum = 1000000);
    AEGISWAR_API bool Epoch(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, double& Value);
    AEGISWAR_API bool CaptureAsc(UAbilitySystemComponent* Asc, int64 CapturedAt, TArray<TSharedPtr<FJsonValue>>& Rows, FString& Error);
    AEGISWAR_API bool RestoreAsc(UAbilitySystemComponent* Asc, const TArray<TSharedPtr<FJsonValue>>& Rows, int64 CurrentUtc, FString& Error, bool Apply = true);
}
