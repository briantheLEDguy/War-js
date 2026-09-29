#include "WarWarpIdol.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
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
    UStaticMesh* AuthoredIdol()
    { return LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Characters/Equipment/WarpIdol.WarpIdol")); }
    double ServerTime(const UWorld* World)
    { const auto* State = World->GetGameState(); return State ? State->GetServerWorldTimeSeconds() : World->GetTimeSeconds(); }
    bool Participant(const AWarCharacter* Pawn)
    {
        if (!IsValid(Pawn) || Pawn->IsDead() || Pawn->IsDevelopmentFlying() || !Pawn->GetController()) return false;
        const auto* Unit = Cast<AWarSiegeCharacter>(Pawn);
        return !Unit || Unit->Unit == EWarSiegeUnit::Participant;
    }
}
AWarWarpIdol::AWarWarpIdol()
{
    bReplicates = true; SetReplicateMovement(true); PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .1f;
    IdolMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AuthoredIdol"));
    SetRootComponent(IdolMesh); IdolMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AWarWarpIdol::BeginPlay()
{
    Super::BeginPlay(); IdolMesh->SetStaticMesh(AuthoredIdol());
    if (!IdolMesh->GetStaticMesh())
    {
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (auto* PC = Cast<AWarPlayerController>(It->Get()); PC && PC->IsLocalController())
                PC->ClientEntryRejected(FText::FromString(TEXT("The Warp Idol model is missing. Repair content and reconnect.")));
        if (HasAuthority()) Destroy();
    }
}
void AWarWarpIdol::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarWarpIdol, Caster); DOREPLIFETIME(AWarWarpIdol, Expires);
    DOREPLIFETIME(AWarWarpIdol, Zone);
    DOREPLIFETIME(AWarWarpIdol, Realm);
}
bool AWarWarpIdol::Placement(const AWarCharacter* Source, FVector& Position, FString& Error)
{
    const auto Fail = [&Error](const TCHAR* Message) { Error = Message; return false; };
    if (!Participant(Source) || !Source->HasAuthority()) return Fail(TEXT("A living participant must place the idol."));
    const auto* State = Source->GetPlayerState<AWarPlayerState>();
    if (!State || State->GetRealm() == EWarRealm::None || State->GetCurrentZone().IsNone()) return Fail(TEXT("Idol owner has no realm or zone."));
    auto* Mesh = AuthoredIdol();
    if (!Mesh || Mesh->GetStaticMaterials().IsEmpty()) return Fail(TEXT("The authored Warp Idol model is missing."));
    if (Source->GetCharacterMovement()->IsFalling()) return Fail(TEXT("Land before placing the idol."));
    FHitResult Floor; FCollisionQueryParams Query(SCENE_QUERY_STAT(IdolPlacement), false, Source);
    const FVector Start = Source->GetActorLocation() + Source->GetActorForwardVector() * 150;
    if (!Source->GetWorld()->LineTraceSingleByChannel(Floor, Start, Start-FVector(0,0,Source->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+60), ECC_Visibility, Query)
        || Floor.ImpactNormal.Z < Source->GetCharacterMovement()->GetWalkableFloorZ()) return Fail(TEXT("The idol requires walkable ground in front of you."));
    Position = Floor.ImpactPoint + FVector(0,0,2);
    FHitResult Obstacle;
    if (Source->GetWorld()->LineTraceSingleByChannel(Obstacle, Source->GetActorLocation(), Position+FVector(0,0,40), ECC_Visibility, Query))
        return Fail(TEXT("The idol cannot be placed through a wall."));
    const FBox Box = Mesh->GetBoundingBox();
    if (Source->GetWorld()->OverlapBlockingTestByChannel(Position+Box.GetCenter(), FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeBox(Box.GetExtent()), Query)) return Fail(TEXT("There is no room for the idol here."));
    return true;
}
bool AWarWarpIdol::Place(AWarCharacter* Source, float Damage, FString& Error)
{
    if (!FMath::IsFinite(Damage) || Damage <= 0 || Damage > 1000000) { Error = TEXT("Invalid idol damage."); return false; }
    FVector Position; if (!Placement(Source, Position, Error)) return false;
    FActorSpawnParameters Params; Params.Owner = Source; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Idol = Source->GetWorld()->SpawnActor<AWarWarpIdol>(Position, FRotator::ZeroRotator, Params);
    if (!IsValid(Idol) || Idol->IsActorBeingDestroyed()) { Error = TEXT("Idol placement failed."); return false; }
    RemoveFor(Source);
    Idol->Caster = Source; Idol->Expires = ServerTime(Source->GetWorld()) + Duration;
    Idol->NextPulse = ServerTime(Source->GetWorld()) + Interval; Idol->PulseDamage = Damage;
    const auto* State = Source->GetPlayerState<AWarPlayerState>(); Idol->Zone = State->GetCurrentZone(); Idol->Realm = State->GetRealm();
    Idol->ForceNetUpdate(); return true;
}
void AWarWarpIdol::RemoveFor(AWarCharacter* Source)
{
    if (!IsValid(Source) || !Source->HasAuthority()) return;
    for (TActorIterator<AWarWarpIdol> It(Source->GetWorld()); It; ++It) if (It->Caster == Source) It->Destroy();
}
bool AWarWarpIdol::HasFor(const AWarCharacter* Source)
{
    if (!IsValid(Source)) return false;
    for (TActorIterator<AWarWarpIdol> It(Source->GetWorld()); It; ++It)
        if (It->Caster == Source && It->IsActive()) return true;
    return false;
}
bool AWarWarpIdol::IsActive() const
{
    if (IsActorBeingDestroyed() || !Participant(Caster) || !IdolMesh->GetStaticMesh() || ServerTime(GetWorld()) >= Expires) return false;
    const auto* State = Caster->GetPlayerState<AWarPlayerState>();
    return State && State->GetRealm() == Realm && State->GetCurrentZone() == Zone
        && FVector::DistSquared(Caster->GetActorLocation(), GetActorLocation()) <= FMath::Square(OwnerLeash);
}
bool AWarWarpIdol::CanAttack(const AActor* Target) const
{
    if (!IsActive() || !IsValid(Target) || Target->GetWorld() != GetWorld()
        || FVector::DistSquared(GetActorLocation(), Target->GetActorLocation()) > FMath::Square(Radius)
        || !Caster->CanAbilityTarget(Target, OwnerLeash + Radius, false)) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(IdolSight), false, this); Query.AddIgnoredActor(Caster);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation()+FVector(0,0,65), Target->GetActorLocation(), ECC_Visibility, Query) || Hit.GetActor() == Target;
}
void AWarWarpIdol::Tick(float Delta)
{
    Super::Tick(Delta); if (!HasAuthority()) return;
    if (!IsActive()) { Destroy(); return; }
    const double Now = ServerTime(GetWorld()); if (Now < NextPulse) return;
    // Missed ticks never accumulate a catch-up damage burst.
    NextPulse = Now + Interval;
    AActor* Target = nullptr; double Distance = TNumericLimits<double>::Max();
    for (TActorIterator<APawn> It(GetWorld()); It; ++It) if (CanAttack(*It))
    {
        const double Candidate = FVector::DistSquared(GetActorLocation(), It->GetActorLocation());
        if (Candidate < Distance || (Candidate == Distance && Target && It->GetUniqueID() < Target->GetUniqueID()))
        { Target = *It; Distance = Candidate; }
    }
    if (!Target) return;
    const auto* Status = UWarCombatStatus::On(Caster);
    UWarCombatStatus::Damage(Target, Caster, PulseDamage * (Status ? Status->OutgoingScale() : 1), OwnerLeash + Radius, false);
}
