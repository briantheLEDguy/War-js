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
    UPROPERTY(EditAnywhere, Category="Crafting") FName StationKind = TEXT("general");
    UPROPERTY(EditAnywhere, Category="Crafting", meta=(ClampMin="1")) float InteractionRadius = 500.f;
    bool CanInteract(const APawn* Pawn) const;
};
