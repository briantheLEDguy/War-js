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
    /** Reparent existing actors without clipboard recreation; preserves identities and component state. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static bool MoveCityGameplayToLevel(const TArray<AActor*>& Actors, ULevelStreaming* Destination);
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

    /** Read actual built LOD buffers, not source-description UV counts. Never modifies or saves the mesh. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static FString DescribeStaticMeshRenderData(UStaticMesh* Mesh);

    /** Read committed source triangle corners and attributes; never uses or changes a pending working copy. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static FString DescribeStaticMeshSourceData(UStaticMesh* Mesh, int32 Lod = 0);

    /** Read every committed stored corner, including unused instances; never touches an editor working copy. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static FString DescribeStaticMeshStoredCorners(UStaticMesh* Mesh, int32 Lod = 0);

    /** Read actual oriented render faces and computed corner basis; no build, save or source-normal inference. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static FString DescribeStaticMeshRenderedFaces(UStaticMesh* Mesh, int32 Lod = 0);

    /** Read persistent source/build/mesh/collision policy through native accessors; no builds, saves or working copies. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static FString DescribeStaticMeshNativePolicy(UStaticMesh* Mesh);

    /** Clone only the measured mountain into a fresh owned citadel package; no source edits or package saves. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static UStaticMesh* CreateCarvedCitadelTerrain(UStaticMesh* SourceMesh, const FString& Collection, const FString& ClippedJson);
#if WITH_DEV_AUTOMATION_TESTS
    /** Unsaved transient source fixtures only; exercises the same importer without touching the real mountain. */
    static UStaticMesh* CreateCarvedCitadelTerrainForAutomation(UStaticMesh* SourceMesh, const FString& Collection, const FString& ClippedJson);
#endif

    /** Configure owned citadel source LODs and build once. Never saves or edits licensed/unowned assets. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static bool ConfigureCitadelSurfaceLods(UStaticMesh* Mesh);

    UFUNCTION(BlueprintCallable, Category="Migration")
    static void PreparePreviewFrame(USkeletalMeshComponent* Component);

    /** Block until current-platform animation data exists; pose verification must not fall back to raw tracks. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static bool PrepareCompressedAnimation(UAnimSequence* Animation);

    /** Finish controller-authored tracks and synchronize compression sampling with the data model. */
    UFUNCTION(BlueprintCallable, Category="Migration")
    static bool FinalizeAnimationSampling(UAnimSequence* Animation);


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
