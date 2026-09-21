#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarImportLibrary.generated.h"

class UAnimSequence;
class UStaticMesh;
class UMaterialInterface;
class USkeletalMeshComponent;
class UBoxComponent;

/** Editor-only import provenance, development terrain construction and render diagnostics. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarImportLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Attach an invisible authored collision volume to an owned capital building. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static UBoxComponent* SetCapitalBuildingCollision(AActor* Actor, int32 Index,
        FVector Center, FVector HalfSize, double YawDegrees);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static FString GetSourceAnimationName(const UAnimSequence* Animation);

    /** Development terrain construction, explicitly allowed technical geometry, not a model fallback. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static UStaticMesh* CreateProofTerrain(UMaterialInterface* Material);

    /** Authored capital ground/canal triangles; never a fallback for scenery. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static UStaticMesh* CreateCapitalSurface(const FString& ZoneId, const FString& Surface,
        const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
        const TArray<FVector2D>& UVs, UMaterialInterface* Material, bool bCollision);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static void PreparePreviewFrame(USkeletalMeshComponent* Component);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static FBox GetSkinnedBounds(USkeletalMeshComponent* Component);
};
