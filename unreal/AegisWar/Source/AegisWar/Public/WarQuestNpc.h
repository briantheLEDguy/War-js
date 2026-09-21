#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarQuestNpc.generated.h"

class UWarCharacterVisualDefinition;
class APawn;
class USkeletalMeshComponent;

/** Trusted world placement binds catalog identity to an imported character; no fallback meshes. */
UCLASS()
class AEGISWAR_API AWarQuestNpc : public AActor
{
    GENERATED_BODY()
public:
    AWarQuestNpc();
    USkeletalMeshComponent* GetSkeletalMeshComponent() const { return Mesh; }
    virtual void BeginPlay() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(EditAnywhere, Replicated, Category="Quest") FName ZoneId;
    UPROPERTY(EditAnywhere, Replicated, Category="Quest") FName NpcId;
    UPROPERTY(EditAnywhere, ReplicatedUsing=OnRep_Visual, Category="Quest") TObjectPtr<UWarCharacterVisualDefinition> Visual;
    bool ResolveInteraction(const APawn* Pawn, FString& Name, FString& Error) const;
    bool ValidateIdentity(FString& Name, FString& Error, bool* bMeasureHeight = nullptr) const;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Mesh;
    UFUNCTION() void OnRep_Visual();
};
