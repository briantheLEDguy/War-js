#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarInteriorAtmosphere.generated.h"

class UBoxComponent;
class UPostProcessComponent;

/** Bounded eye adaptation for furnished T1 rooms; it never replaces the regional clock. */
UCLASS()
class AEGISWAR_API AWarInteriorAtmosphere : public AActor
{
    GENERATED_BODY()
public:
    AWarInteriorAtmosphere();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> RoomBounds;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPostProcessComponent> Exposure;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere") FName ZoneId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere", meta=(ClampMin="-4",ClampMax="8")) float DayExposureBias=2.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Regional atmosphere", meta=(ClampMin="-4",ClampMax="8")) float NightExposureBias=3.5f;
    void ApplyTime(double Seconds);
    virtual void Tick(float DeltaSeconds) override;
};
