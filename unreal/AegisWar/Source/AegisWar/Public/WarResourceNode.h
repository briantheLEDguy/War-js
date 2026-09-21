#pragma once
#include "CoreMinimal.h"
#include "Engine/StaticMeshActor.h"
#include "WarGatheringRules.h"
#include "WarResourceNode.generated.h"

/** Placed by trusted world import/GM publication; never creates placeholder geometry. */
UCLASS()
class AEGISWAR_API AWarResourceNode : public AStaticMeshActor
{
    GENERATED_BODY()
public:
    AWarResourceNode();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated, EditAnywhere, Category="Gathering") FName ZoneId;
    UPROPERTY(Replicated, EditAnywhere, Category="Gathering") FName NodeId;
    UPROPERTY(Replicated, EditAnywhere, Category="Gathering") FName VisualPropId;
    bool ResolveInteraction(const APawn* Pawn, FWarResourceDefinition& Definition, FString& Error) const;
};
