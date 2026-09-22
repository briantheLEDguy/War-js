#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarZoneStreamingSubsystem.generated.h"

class AWarCharacter;
class AWarZonePortal;
class APlayerController;
class AWarPlayerController;

/** Development same-server streaming. Production admission and durable handoff remain separate gates. */
UCLASS()
class AEGISWAR_API UWarZoneStreamingSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    bool IsZoneReady(FName Zone, const APlayerController* Player = nullptr, FString* OutReason = nullptr) const;
    bool EnsureZone(FName Zone, FString& Error);
    static bool RequiresActorCollisionReadiness(const AActor* Actor);
    bool QueuePortal(AWarZonePortal* Portal, AWarCharacter* Character, FName Destination, FString& Error);
    bool QueueGmZone(AWarPlayerController* Player, FName Destination, FString& Error);
    bool HasPending(const AWarCharacter* Character) const;
    void Cancel(AWarCharacter* Character);
    static bool CanContinue(bool bSamePawn, bool bAlive, bool bVisualReady, double Distance,
        double Radius, double Now, double Deadline);
private:
    struct FPending
    {
        TWeakObjectPtr<AWarZonePortal> Portal;
        TWeakObjectPtr<AWarCharacter> Character;
        TWeakObjectPtr<APlayerController> Player;
        FName Destination;
        double Deadline = 0;
        bool bGm = false;
        FVector SourcePosition = FVector::ZeroVector;
    };
    TArray<FPending> Pending;
    TMap<FName, double> KeepUntil;
    TMap<TWeakObjectPtr<APlayerController>, TSet<FName>> ClientPackages;
    double NextUpdateAt = 0;
    void UpdateStreaming();
};
