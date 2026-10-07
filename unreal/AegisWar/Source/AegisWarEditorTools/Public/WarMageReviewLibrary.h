#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WarMageReviewLibrary.generated.h"

class UAnimSequence;
class USkeleton;
class USkeletalMesh;

/** Private review diagnostics. No registration, original-asset edits, package saves or art approval. */
UCLASS()
class AEGISWAREDITORTOOLS_API UWarMageReviewLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Read actual mesh reference and inverse bind bases, independently of its assigned skeleton. */
    UFUNCTION(BlueprintCallable, Category="Migration|MageReview")
    static FString DescribeSkeletalReference(const USkeletalMesh* Mesh);

    /** Read the copied/original skeleton reference without modification. */
    UFUNCTION(BlueprintCallable, Category="Migration|MageReview")
    static FString DescribeSkeletonReference(const USkeleton* Skeleton);

    /** Rebind only a private duplicated sequence to a private copy with identical reference data. */
    UFUNCTION(BlueprintCallable, Category="Migration|MageReview")
    static bool AssignDiagnosticSequenceSkeleton(UAnimSequence* Sequence, USkeleton* Skeleton,
        const FString& CandidateRoot);
};
