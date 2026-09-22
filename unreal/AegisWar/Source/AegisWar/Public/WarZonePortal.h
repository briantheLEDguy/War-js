#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarZonePortal.generated.h"

class USphereComponent;
class UTextRenderComponent;
class AWarCharacter;

/** Development same-server zone traversal. Never performs whole-server map travel. */
UCLASS()
class AEGISWAR_API AWarZonePortal : public AActor
{
    GENERATED_BODY()
public:
    AWarZonePortal();
    virtual void OnConstruction(const FTransform& Transform) override;
    UPROPERTY(EditAnywhere, Category="Portal") FName RouteId;
    UPROPERTY(EditAnywhere, Category="Portal") FName DestinationRouteId;
    UPROPERTY(EditAnywhere, Category="Portal") FText DestinationLabel;
    UPROPERTY(EditAnywhere, Category="Portal") FVector ArrivalLocation = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Portal") float Radius = 900.f;
    UPROPERTY(EditAnywhere, Category="Portal") bool bDestinationBuilt = false;
    bool TryTraverse(AWarCharacter* Character, FString& Error);
    static double CapsuleGroundOffset(double HalfHeight, double CapsuleRadius, double NormalZ);
    static bool CanEnter(bool bAuthority, bool bDevelopment, bool bAlive, bool bVisualReady,
        bool bDestinationReady, double Distance, double EntryRadius, double Now, double AllowedAt);
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> Trigger;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UTextRenderComponent> Label;
    TMap<TWeakObjectPtr<AWarCharacter>, double> AllowedAfter;
    UFUNCTION() void Enter(UPrimitiveComponent* Component, AActor* Other, UPrimitiveComponent* OtherComponent,
        int32 BodyIndex, bool bSweep, const FHitResult& Hit);
};
