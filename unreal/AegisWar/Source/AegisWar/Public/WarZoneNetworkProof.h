#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarZoneNetworkProof.generated.h"

/** Opt-in two-client level isolation proof. No production admission or persistence claim. */
UCLASS()
class AEGISWAR_API UWarZoneNetworkProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
private:
    void Finish(bool bPassed, const FString& Detail);
    void InspectClientResidency();
    FName LastClientZone;
    double ClientSettledAt = 0;
    TWeakObjectPtr<class APlayerController> Traveler;
    TWeakObjectPtr<class APlayerController> Resident;
    TWeakObjectPtr<class AWarCharacter> TravelPawn;
    FVector ResidentPosition = FVector::ZeroVector;
    int32 Revision = 0;
    int32 Stage = 0;
    double NextCheck = 0;
    double Deadline = 150;
    bool bFinished = false;
};
