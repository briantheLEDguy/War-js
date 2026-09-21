#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "WarCraftingRules.h"
#include "WarCultivationRules.h"
#include "WarGatheringRules.h"
#include "WarQuestRules.h"
#include "WarContentSubsystem.generated.h"

class FJsonObject;
class UWarCharacterVisualDefinition;

struct AEGISWAR_API FWarVisualImportBinding
{
    FString SourceModel;
    FString SourceSha256;
    FString SkeletalMeshPath;
    TSet<FString> AnimationPaths;
};

USTRUCT(BlueprintType)
struct AEGISWAR_API FWarContentSummary
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FString SourceSha256;
    UPROPERTY(BlueprintReadOnly) int32 MapCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 DevelopmentMapCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 CareerCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 AbilityCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 ItemCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 QuestCount = 0;
    UPROPERTY(BlueprintReadOnly) int32 RecipeCount = 0;
};

/** Loads the portable catalog contract. It does not claim those gameplay systems are ported. */
UCLASS()
class AEGISWAR_API UWarContentSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintPure, Category="Migration") bool IsContentReady() const { return bReady; }
    UFUNCTION(BlueprintPure, Category="Migration") FWarContentSummary GetSummary() const { return Summary; }
    UFUNCTION(BlueprintPure, Category="Migration") FString GetValidationError() const { return ValidationError; }

    static bool ParseManifest(const FString& Json, FWarContentSummary& OutSummary, FString& OutError);
    static bool ParseVisualImports(const FString& Json, TMap<FName, FWarVisualImportBinding>& OutBindings, FString& OutError);
    static bool ValidateVisualImportBinding(const UWarCharacterVisualDefinition* Visual,
        const TMap<FName, FWarVisualImportBinding>& Bindings, FString& OutError);
    bool ValidatePlayableVisual(const UWarCharacterVisualDefinition* Visual, FString& OutError) const;
    FText GetItemDisplayName(FName Key) const;
    bool GetConsumableEffect(FName Key, float& Health, float& Mana) const;
    bool GetResourceNode(FName ZoneId, FName NodeId, FWarResourceDefinition& Node, FString& Error) const;
    static bool ParseResourceNode(const TSharedPtr<FJsonObject>& Catalog, FName ZoneId, FName NodeId, FWarResourceDefinition& Node, FString& Error);
    bool GetCultivationSeed(FName Key, FWarCultivationSeed& Seed, FString& Error) const;
    static bool ParseCultivationSeed(const TSharedPtr<FJsonObject>& Catalog, FName Key, FWarCultivationSeed& Seed, FString& Error);
    bool GetQuest(FName Id, FWarQuestDefinition& Quest, FString& Error) const;
    TArray<FWarQuestDefinition> GetQuestsForNpc(FName Zone, FName Npc) const;
    bool GetQuestNpc(FName Zone, FName Npc, FString& Name, FName& Profile, FString& Error, bool* bMeasureHeight = nullptr) const;
    static bool ParseQuestNpc(const TSharedPtr<FJsonObject>& Catalog, FName Zone, FName Npc,
        FString& Name, FName& Profile, FString& Error, bool* bMeasureHeight = nullptr);
    bool ValidateNpcVisual(const UWarCharacterVisualDefinition* Visual, FName Profile, FString& Error) const;
    static bool ParseQuestCatalog(const TSharedPtr<FJsonObject>& Catalog,
        TMap<FName, FWarQuestDefinition>& Quests, FString& Error);
    bool GetCraftRecipe(FName Id, FWarCraftRecipe& Recipe, FString& Error) const;
    bool ResolveInventoryItem(FName Key, int32 Quantity, FWarInventoryItem& Item) const;
    TArray<FName> GetCraftRecipeIds() const;
    static bool ParseCraftRecipe(const TSharedPtr<FJsonObject>& Catalog, FName Id, FWarCraftRecipe& Recipe, FString& Error);
private:
    UPROPERTY() FWarContentSummary Summary;
    UPROPERTY() FString ValidationError;
    bool bReady = false;
    TSharedPtr<FJsonObject> Manifest;
    TMap<FName, FWarVisualImportBinding> VisualImports;
    FString VisualImportError;
    TMap<FName, FWarQuestDefinition> QuestCatalog;
};
