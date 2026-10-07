#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarMageMeshBufferReadback.generated.h"

class USkeletalMesh;

/** Restricted, read-only CPU mirrors of actual native LOD0 render buffers; never changes CPU access/build state. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarMageMeshBufferReadback : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Migration|MageReview")
    static FString DescribeFaceRenderBuffers(const USkeletalMesh* Mesh, const TArray<int32>& MaterialSlots);
};
