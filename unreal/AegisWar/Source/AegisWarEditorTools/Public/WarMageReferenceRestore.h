#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarMageReferenceRestore.generated.h"

class USkeletalMesh;

/** Copies a proven original reference only onto a private diagnostic mesh; never accepts arbitrary transforms. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarMageReferenceRestore : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Migration|MageReview")
    static bool RestoreDiagnosticMeshReference(USkeletalMesh* Candidate,
        const USkeletalMesh* Original, const FString& CandidateRoot);
};
