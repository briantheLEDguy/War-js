#pragma once
#include "CoreMinimal.h"
class AActor;

/** Trusted authored light data, never supplied by a GM draft or network client. */
struct FWarWorldEditPracticalLight
{
    FName SourceActor;
    FTransform RelativeTransform;
    bool bVisible = true;
    bool bHidden = false;
    TMap<FName, FString> Properties;
};

namespace WarWorldEditPracticalLights
{
    bool Capture(AActor* Parent, TArray<FWarWorldEditPracticalLight>& Out, FString& Error);
    bool Matches(AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Expected);
    bool Create(AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Templates, FString& Error);
    bool MatchesCreated(const AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Templates);
    void SetHidden(AActor* Parent, const TArray<FWarWorldEditPracticalLight>& Templates, bool bHidden);
    void DestroyAttached(AActor* Parent);
}
