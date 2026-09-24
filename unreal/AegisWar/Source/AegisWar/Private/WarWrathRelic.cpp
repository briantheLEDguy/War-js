#include "WarWrathRelic.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarCombatStatus.h"
#include "WarSiegeGameMode.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

namespace
{
    UStaticMesh* AuthoredRelic()
    { return LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Characters/Equipment/IconOfWrath.IconOfWrath")); }
    double ServerTime(const UWorld* World)
    { const auto* State = World->GetGameState(); return State ? State->GetServerWorldTimeSeconds() : World->GetTimeSeconds(); }
    bool Participant(const AWarCharacter* Pawn)
    {
        if (!IsValid(Pawn) || Pawn->IsDead() || Pawn->IsDevelopmentFlying() || !Pawn->GetController()) return false;
        const auto* Unit = Cast<AWarSiegeCharacter>(Pawn);
        return !Unit || Unit->Unit == EWarSiegeUnit::Participant;
    }
}

AWarWrathRelic::AWarWrathRelic()
{
    bReplicates = true; SetReplicateMovement(true); PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .05f;
    RelicMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AuthoredRelic"));
    SetRootComponent(RelicMesh); RelicMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AWarWrathRelic::BeginPlay()
{ Super::BeginPlay(); RelicMesh->SetStaticMesh(AuthoredRelic()); }
void AWarWrathRelic::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarWrathRelic, Caster); DOREPLIFETIME(AWarWrathRelic, Expires);
    DOREPLIFETIME(AWarWrathRelic, Zone); DOREPLIFETIME(AWarWrathRelic, Realm);
}
bool AWarWrathRelic::Placement(const AWarCharacter* Source, FVector& Position, FString& Error)
{
    const auto Fail = [&Error](const TCHAR* Message) { Error = Message; return false; };
    if (!Participant(Source) || !Source->HasAuthority()) return Fail(TEXT("A living participant must place the relic."));
    const auto* State = Source->GetPlayerState<AWarPlayerState>();
    if (!State || State->GetRealm() == EWarRealm::None || State->GetCurrentZone().IsNone()) return Fail(TEXT("Relic owner has no active realm and zone."));
    auto* Mesh = AuthoredRelic();
    if (!Mesh || Mesh->GetStaticMaterials().IsEmpty()) return Fail(TEXT("The authored Icon of Wrath model is missing."));
    if (Source->GetCharacterMovement()->IsFalling()) return Fail(TEXT("Land before placing the relic."));
    FHitResult Floor; FCollisionQueryParams Query(SCENE_QUERY_STAT(WrathPlacement), false, Source);
    const FVector Start = Source->GetActorLocation();
    if (!Source->GetWorld()->LineTraceSingleByChannel(Floor, Start, Start-FVector(0,0,Source->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+50), ECC_Visibility, Query)
        || Floor.ImpactNormal.Z < Source->GetCharacterMovement()->GetWalkableFloorZ()) return Fail(TEXT("Relic requires walkable ground beneath you."));
    Position = Floor.ImpactPoint + FVector(0,0,2);
    // Test the actual authored bounds, not a point placement that can enter walls.
    const FBox Box = Mesh->GetBoundingBox();
    if (Source->GetWorld()->OverlapBlockingTestByChannel(Position+Box.GetCenter(), FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeBox(Box.GetExtent()), Query)) return Fail(TEXT("There is no room for the relic here."));
    return true;
}
bool AWarWrathRelic::Place(AWarCharacter* Source, FString& Error)
{
    FVector Position; if (!Placement(Source, Position, Error)) return false;
    FActorSpawnParameters Params; Params.Owner = Source; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Relic = Source->GetWorld()->SpawnActor<AWarWrathRelic>(Position, FRotator::ZeroRotator, Params);
    if (!Relic) { Error = TEXT("Relic placement failed."); return false; }
    RemoveFor(Source);
    Relic->Caster = Source; Relic->Expires = ServerTime(Source->GetWorld())+Duration;
    const auto* State = Source->GetPlayerState<AWarPlayerState>(); Relic->Zone = State->GetCurrentZone(); Relic->Realm = State->GetRealm();
    Relic->ForceNetUpdate(); return true;
}
void AWarWrathRelic::RemoveFor(AWarCharacter* Source)
{
    if (!IsValid(Source) || !Source->HasAuthority()) return;
    for (TActorIterator<AWarWrathRelic> It(Source->GetWorld()); It; ++It) if (It->Caster == Source) It->Destroy();
}
bool AWarWrathRelic::IsActive() const
{
    if (IsActorBeingDestroyed() || !Participant(Caster) || ServerTime(GetWorld()) >= Expires) return false;
    const auto* State = Caster->GetPlayerState<AWarPlayerState>();
    return State && State->GetCurrentZone() == Zone && State->GetRealm() == Realm;
}
bool AWarWrathRelic::CanBenefit(const AWarCharacter* Dealer) const
{
    if (!IsActive() || !Participant(Dealer) || Dealer->GetWorld() != GetWorld()) return false;
    const auto* State = Dealer->GetPlayerState<AWarPlayerState>();
    if (!State || State->GetRealm() != Realm || State->GetCurrentZone() != Zone
        || FVector::DistSquared(GetActorLocation(), Dealer->GetActorLocation()) > FMath::Square(Radius)) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WrathSight), false, this);
    Query.AddIgnoredActor(Caster);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation()+FVector(0,0,35), Dealer->GetActorLocation(), ECC_Visibility, Query) || Hit.GetActor() == Dealer;
}
void AWarWrathRelic::HostileHealthDamage(AWarCharacter* Dealer, float HealthLost)
{
    if (!IsValid(Dealer) || !Dealer->HasAuthority() || !FMath::IsFinite(HealthLost) || HealthLost <= 0) return;
    for (TActorIterator<AWarWrathRelic> It(Dealer->GetWorld()); It; ++It) if (It->CanBenefit(Dealer))
    {
        // Healing emits no damage event. Return after the first eligible field:
        // overlapping fields cannot multiply the proc or cause recursive healing.
        UWarCombatStatus::Heal(Dealer, HealthLost*HealFraction); return;
    }
}
void AWarWrathRelic::Tick(float Delta)
{ Super::Tick(Delta); if (HasAuthority() && !IsActive()) Destroy(); }
