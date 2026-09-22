#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarImportLibrary.generated.h"

class UAnimSequence;
class UStaticMesh;
class UMaterialInterface;
class USkeletalMeshComponent;
class UBoxComponent;
class ULevelStreaming;

/** Editor-only import provenance, development terrain construction and render diagnostics. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarImportLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Commandlet-safe copy of explicitly owned, unattached campaign actors; source actors are retained. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static TArray<AActor*> CopyCampaignActorsToLevel(const TArray<AActor*>& Actors, ULevelStreaming* Destination);
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

    /** Source-derived world terrain/static surfaces, isolated by build collection. No fallback geometry. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static UStaticMesh* CreateWorldSurface(const FString& Collection, const FString& Key,
        const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
        const TArray<FVector2D>& UVs, UMaterialInterface* Material, bool bCollision);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static UStaticMesh* CreateColoredWorldSurface(const FString& Collection, const FString& Key,
        const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
        const TArray<FVector2D>& UVs, const TArray<FLinearColor>& VertexColors, UMaterialInterface* Material, bool bCollision);

    /** Preserve every source surface and material in one editable/interactive mesh. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static UStaticMesh* CreateCompositeWorldSurface(const FString& Collection, const FString& Key,
        const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
        const TArray<FVector2D>& UVs, const TArray<FLinearColor>& VertexColors,
        const TArray<int32>& TriangleMaterials, const TArray<UMaterialInterface*>& Materials, bool bCollision);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static void PreparePreviewFrame(USkeletalMeshComponent* Component);

    /** Block until current-platform animation data exists; pose verification must not fall back to raw tracks. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static bool PrepareCompressedAnimation(UAnimSequence* Animation);


    UFUNCTION(BlueprintCallable, Category="Migration")
    static void PrepareWorldPreviewFrame(UWorld* World);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static FBox GetSkinnedBounds(USkeletalMeshComponent* Component);
private:
    static UStaticMesh* BuildSurface(const FString& PackageName, const FString& Owner,
        const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
        const TArray<FVector2D>& UVs, UMaterialInterface* Material, bool bCollision,
        const TArray<FLinearColor>& VertexColors = TArray<FLinearColor>(),
        const TArray<int32>& TriangleMaterials = TArray<int32>(),
        const TArray<UMaterialInterface*>& Materials = TArray<UMaterialInterface*>());
};
