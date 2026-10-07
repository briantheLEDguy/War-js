#pragma once
#include "CoreMinimal.h"
#include "Engine/PointLight.h"
#include "WarPracticalLight.generated.h"

/** Local illumination attached to admitted village fixtures; time comes from the realm clock. */
UCLASS()
class AEGISWAR_API AWarPracticalLight : public APointLight
{
    GENERATED_BODY()
public:
    AWarPracticalLight();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") FName ZoneId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere", meta=(ClampMin="0",ClampMax="5000")) float NightLumens=900;
    void ApplyTime(double Seconds);
    virtual void Tick(float DeltaSeconds) override;
};
