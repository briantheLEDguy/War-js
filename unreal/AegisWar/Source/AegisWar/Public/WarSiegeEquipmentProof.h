#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarSiegeEquipmentProof.generated.h"
class AWarSiegeBattlefield;
class AWarSiegeEquipment;
UCLASS()
class AEGISWAR_API UWarSiegeEquipmentProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
private:
    bool Engineer(AWarSiegeEquipment* Vehicle,int32 Seat,FString& Error);
    void ObserveClient();
    void Capture(const FString& Name);
    void Finish(bool Passed,const FString& Detail);
    bool GateBlocks(int32 Index) const;
    UPROPERTY() TObjectPtr<AWarSiegeBattlefield> Battlefield;
    UPROPERTY() TArray<TObjectPtr<AWarSiegeEquipment>> Vehicles;
    double Started=-1,LastMove=0,NextSnapshot=0;
    float PreviousTravel=0;
    int32 Step=0;
    bool Finished=false,StopVerified=false,DeathVerified=false,StrikeVerified=false,RecoveryVerified=false;
    bool GateInitiallyClosed=false,GateVerified=false;
    UPROPERTY() TObjectPtr<class ACameraActor> Camera;
    TSet<FString> Captured;
    double ClientFinishedAt=-1;
    double ClientReadyAt=-1;
    double ClaimSeenAt=-1;
    int32 LastClaims=-1;
};
