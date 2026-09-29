#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WarTypes.h"
#include "WarWarpIdol.generated.h"

class AWarCharacter;
class UStaticMeshComponent;

/** One non-blocking, timed deployable per caster; all targeting stays on the server. */
UCLASS()
class AEGISWAR_API AWarWarpIdol : public AActor
{
    GENERATED_BODY()
public:
    AWarWarpIdol();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    static constexpr float Duration = 30.f;
    static constexpr float Radius = 1200.f;
    static constexpr float OwnerLeash = 2000.f;
    static constexpr float Interval = 2.f;
    static bool Placement(const AWarCharacter* Source, FVector& Position, FString& Error);
    static bool Place(AWarCharacter* Source, float Damage, FString& Error);
    static void RemoveFor(AWarCharacter* Source);
    static bool HasFor(const AWarCharacter* Source);
    bool IsActive() const;
    bool CanAttack(const AActor* Target) const;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> IdolMesh;
    UPROPERTY(Replicated) TObjectPtr<AWarCharacter> Caster;
    UPROPERTY(Replicated) double Expires = 0;
    UPROPERTY(Replicated) FName Zone;
    UPROPERTY(Replicated) EWarRealm Realm = EWarRealm::None;
    float PulseDamage = 0;
    double NextPulse = 0;
};
