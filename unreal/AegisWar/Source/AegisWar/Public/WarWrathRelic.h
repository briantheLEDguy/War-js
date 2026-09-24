#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarTypes.h"
#include "WarWrathRelic.generated.h"

class AWarCharacter;
class UStaticMeshComponent;

/** Server-owned, non-stacking damage-to-health field. No client proc requests. */
UCLASS()
class AEGISWAR_API AWarWrathRelic : public AActor
{
    GENERATED_BODY()
public:
    AWarWrathRelic();
    virtual void Tick(float Delta) override;
    virtual void BeginPlay() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    static constexpr float Radius = 500.f;
    static constexpr float Duration = 10.f;
    static constexpr float HealFraction = .1f;
    static bool Placement(const AWarCharacter* Caster, FVector& Position, FString& Error);
    static bool Place(AWarCharacter* Caster, FString& Error);
    static void RemoveFor(AWarCharacter* Caster);
    /** Call once with the actual, clamped health loss after a validated hostile hit. */
    static void HostileHealthDamage(AWarCharacter* Dealer, float HealthLost);
    bool CanBenefit(const AWarCharacter* Participant) const;
    bool IsActive() const;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> RelicMesh;
    UPROPERTY(Replicated) TObjectPtr<AWarCharacter> Caster;
    UPROPERTY(Replicated) double Expires = 0;
    UPROPERTY(Replicated) FName Zone;
    UPROPERTY(Replicated) EWarRealm Realm = EWarRealm::None;
};
