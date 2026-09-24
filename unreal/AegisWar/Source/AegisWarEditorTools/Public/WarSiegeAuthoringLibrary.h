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
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static bool BuildNavigation(UWorld* World, FVector Center, FVector Extent);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static bool NavigationBusy(UWorld* World);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static FString ProbeNavigation(UWorld* World, const TArray<FVector>& Points);
    UFUNCTION(BlueprintCallable, Category="War|Siege")
    static AActor* CreateAssembly(UWorld* World, const FString& Label, const TArray<UStaticMesh*>& Meshes,
        const TArray<FTransform>& Transforms, bool bStageGate);
};
