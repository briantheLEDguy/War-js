#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarSiegeAuthoringLibrary.generated.h"

/** Editor-only navigation authoring; never grants traversal or content approval. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarSiegeAuthoringLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    static bool IsPrivateCampaignNavigationPair(const FString& CampaignPackage, const FString& OverlayPackage);
    /** Transfers existing baked data in place; never rebuilds or grants campaign admission. */
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static FString OwnCampaignNavigation(UWorld* World, const FString& OverlayPackage);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static FString DescribeBakedNavigation(UWorld* World);
    /** Rebuilds only the exact receipted campaign pair; save/reload and runtime proofs remain separate. */
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static FString RebuildCampaignNavigation(UWorld* World, const FString& OverlayPackage,
        const FString& CityRevision, const TArray<FString>& ExpectedAttachments, const TArray<FString>& ExpectedLoadedPackages);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static bool BuildNavigation(UWorld* World, FVector Center, FVector Extent);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static bool NavigationBusy(UWorld* World);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    /** A bounded diagnostic override copies the filter; it never changes saved or runtime navigation. */
    static FString ProbeNavigation(UWorld* World, const TArray<FVector>& Points, int32 DiagnosticMaxSearchNodes = 0);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static AActor* CreateAssembly(UWorld* World, const FString& Label, const TArray<UStaticMesh*>& Meshes,
        const TArray<FTransform>& Transforms, bool bStageGate);
};
