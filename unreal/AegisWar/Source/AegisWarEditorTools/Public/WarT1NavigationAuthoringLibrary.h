#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarT1NavigationAuthoringLibrary.generated.h"

/** Private T1 editor authoring. Baked paths do not establish physical vehicle traversal. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarT1NavigationAuthoringLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    static bool IsPrivateCandidate(const FString& Package, FName Zone);
    /** Scenery ownership may be large; navigation samples only the playable outline envelope. */
    static bool NavigationBounds(const FBox2D& Content, const TArray<FVector2D>& Outline, FBox2D& Result, FString& Error);
    /** Partitions the rectangular backdrop outside a simple, possibly concave footprint. */
    static bool ExteriorCells(const FBox2D& Bounds, const TArray<FVector2D>& Outline,
        TArray<TArray<FVector2D>>& Cells, FString& Error);
    UFUNCTION(BlueprintCallable, Category="War|T1")
    static FString BuildNavigation(UWorld* World, FName Zone, const TArray<FString>& ExpectedAttachments,
        double MinimumHeight, double MaximumHeight);
    /** Uses the actual selected profile and its runtime query budget, without partial paths. */
    UFUNCTION(BlueprintCallable, Category="War|T1")
    static FString ProbeRoute(UWorld* World, FName Zone, bool bConvoy, const TArray<FVector>& Points);
};
