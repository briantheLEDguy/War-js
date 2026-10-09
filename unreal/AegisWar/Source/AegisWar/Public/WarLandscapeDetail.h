#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarLandscapeDetail.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

/** Cosmetic source-model clusters. Terrain and retained actors own all gameplay collision. */
UCLASS()
class AEGISWAR_API AWarLandscapeDetail : public AActor
{
    GENERATED_BODY()
public:
    AWarLandscapeDetail();
    static constexpr int32 MaximumInstances=12000;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Details;
    /** Trusted authoring only; malformed batches leave the previous cluster intact. */
    UFUNCTION(BlueprintCallable,Category="Landscape authoring") bool Configure(UStaticMesh* Mesh,const TArray<FTransform>& Transforms);
    virtual void BeginPlay() override;
};
