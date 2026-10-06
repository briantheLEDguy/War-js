#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "WarCityDefinition.generated.h"

/** Shared scenery only. Campaign services and siege objectives belong to their own overlays. */
UCLASS(BlueprintType)
class AEGISWAR_API UWarCityDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) FName ZoneId;
    UPROPERTY(EditAnywhere) FVector Origin = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) FString Revision;
    UPROPERTY(EditAnywhere) TArray<TSoftObjectPtr<UWorld>> SceneryLevels;
    bool Validate(FString& Error) const;
    TArray<FName> Packages() const;
    UFUNCTION(BlueprintCallable, Category="City")
    static bool IsSceneryActor(const AActor* Actor);
    static bool ValidateLevel(const class ULevel* Level, FString& Error);
};
