#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "WarRuntimeSettings.generated.h"

class UWarCharacterVisualDefinition;
class UWarNpcEquipmentCatalog;

UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="Aegis War migration"))
class AEGISWAR_API UWarRuntimeSettings : public UDeveloperSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(Config, EditAnywhere, Category="Content")
    FString ContentManifestRelativePath = TEXT("Migration/content.json");

    UPROPERTY(Config, EditAnywhere, Category="Content")
    TSoftObjectPtr<UWarNpcEquipmentCatalog> NpcEquipmentCatalog = TSoftObjectPtr<UWarNpcEquipmentCatalog>(
        FSoftObjectPath(TEXT("/Game/WorldRebuild/NpcEquipment/CombatLoadouts.CombatLoadouts")));

    /** Local workbench convenience only; never grants access in Shipping or networked worlds. */
    UPROPERTY(Config, EditAnywhere, Category="Development", meta=(DisplayName="Enable local development GM"))
    bool bEnableLocalDevelopmentGM = false;

    UPROPERTY(Config, EditAnywhere, Category="Development", meta=(AllowedClasses="/Script/AegisWar.WarCharacterVisualDefinition"))
    TSoftObjectPtr<UWarCharacterVisualDefinition> AegisDevelopmentVisual;

    UPROPERTY(Config, EditAnywhere, Category="Development", meta=(AllowedClasses="/Script/AegisWar.WarCharacterVisualDefinition"))
    TSoftObjectPtr<UWarCharacterVisualDefinition> RiftboundDevelopmentVisual;
};
