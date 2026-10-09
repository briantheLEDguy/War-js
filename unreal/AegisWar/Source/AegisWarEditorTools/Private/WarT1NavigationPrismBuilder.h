#pragma once
#include "CoreMinimal.h"
#include "Engine/BrushBuilder.h"
#include "WarT1NavigationPrismBuilder.generated.h"

/** Serializable convex exclusion brush, with no rendered geometry or physical collision. */
UCLASS()
class UWarT1NavigationPrismBuilder : public UBrushBuilder
{
    GENERATED_BODY()
public:
    UPROPERTY() TArray<FVector2D> Hull;
    UPROPERTY() double HalfHeight = 1;
    virtual bool Build(UWorld* World, ABrush* Brush = nullptr) override;
};
