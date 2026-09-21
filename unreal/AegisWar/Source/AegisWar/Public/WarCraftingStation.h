#pragma once

#include "CoreMinimal.h"
#include "Engine/StaticMeshActor.h"
#include "WarCraftingStation.generated.h"

UCLASS()
class AEGISWAR_API AWarCraftingStation : public AStaticMeshActor
{
    GENERATED_BODY()
public:
    AWarCraftingStation();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated, EditAnywhere, Category="Crafting") FName StationKind = TEXT("general");
    UPROPERTY(Replicated, EditAnywhere, Category="Crafting", meta=(ClampMin="1")) float InteractionRadius = 500.f;
    bool CanInteract(const APawn* Pawn) const;
};
