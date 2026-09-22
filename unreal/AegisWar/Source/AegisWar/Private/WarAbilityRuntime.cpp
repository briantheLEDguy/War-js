#include "WarAbilityRuntime.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCombatStatus.h"
#include "AbilitySystemComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"

UWarAbilityRuntime::UWarAbilityRuntime()
{ SetIsReplicatedByDefault(true); PrimaryComponentTick.bCanEverTick = true; }
void UWarAbilityRuntime::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UWarAbilityRuntime, Career, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UWarAbilityRuntime, Resource, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UWarAbilityRuntime, GcdUntil, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UWarAbilityRuntime, BusyUntil, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UWarAbilityRuntime, Cooldowns, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UWarAbilityRuntime, Casting, COND_OwnerOnly);
}
double UWarAbilityRuntime::Now() const
{ const auto* State = GetWorld()->GetGameState(); return State ? State->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds(); }
UWarAbilityCatalog* UWarAbilityRuntime::Catalog() const
{ return GetWorld()->GetGameInstance() ? GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>() : nullptr; }
AWarCharacter* UWarAbilityRuntime::Avatar() const
{ const auto* State = Cast<AWarPlayerState>(GetOwner()); return State ? Cast<AWarCharacter>(State->GetPawn()) : nullptr; }
void UWarAbilityRuntime::InitializeCharacter(AWarCharacter* Pawn)
{
    if (!GetOwner()->HasAuthority() || !Pawn) return;
    Cancel();
    if (Career != Pawn->GetCareerId())
    {
        Career = Pawn->GetCareerId(); Cooldowns.Reset(); GcdUntil = 0;
        const auto Kit = Catalog() ? Catalog()->Kit(Career) : TArray<const FWarAbilityDefinition*>();
        Resource = Kit.IsEmpty() ? 0 : Kit[0]->ResourceInitial;
    }
}
float UWarAbilityRuntime::Cooldown(FName Id) const
{
    const auto* Entry = Cooldowns.FindByPredicate([Id](const auto& C) { return C.Id == Id; });
    return FMath::Max(0., FMath::Max(GcdUntil, Entry ? Entry->Until : 0.) - Now());
}
bool UWarAbilityRuntime::CanActivate(const FWarAbilityDefinition& A, AActor* Target, FString& Error, bool bCheckMovement) const
{
    Error.Reset(); const auto* Pawn = Avatar(); const auto* State = Cast<AWarPlayerState>(GetOwner());
    const auto Fail = [&Error](const FString& Message) { Error = Message; return false; };
    if (!Pawn || !State || !Pawn->IsVisualReady() || Pawn->IsDead() || Pawn->IsDevelopmentFlying()) return Fail(TEXT("Character is not ready for combat."));
    if (A.Career != Career || Career != Pawn->GetCareerId()) return Fail(TEXT("This ability belongs to another class."));
    if (!A.UnavailableReason.IsEmpty()) return Fail(A.UnavailableReason);
    if (State->GetInventory().CharacterProgression.Level < A.UnlockLevel) return Fail(FString::Printf(TEXT("Unlocks at level %d."), A.UnlockLevel));
    if (Cooldown(A.Id) > 0 || IsBusy() || Pawn->IsActionPlaying()) return Fail(TEXT("Wait for the current action or cooldown."));
    const auto* Status = UWarCombatStatus::On(Pawn);
    TArray<FName> Cleanses;
    for (const auto& E : A.Effects) Cleanses.Append(E.Cleanse);
    if (Status && ((Status->Has(TEXT("stagger")) && !Cleanses.Contains(TEXT("stagger"))) || (A.bBlockedBySilence && Status->Has(TEXT("silence"))))) return Fail(TEXT("Cannot act while staggered or silenced."));
    if (!State->GetAttributes() || State->GetAttributes()->GetMana() < A.Mana) return Fail(FString::Printf(TEXT("Requires %.0f mana."), A.Mana));
    if (Resource < FMath::Max(A.Cost, A.MinimumResource)) return Fail(FString::Printf(TEXT("Requires %.0f %s."), FMath::Max(A.Cost, A.MinimumResource), *A.ResourceLabel));
    if (A.bEnemyTarget && !Pawn->CanAbilityTarget(Target, A.Range)) return Fail(TEXT("Select a living hostile in range with a clear line of sight."));
    if (Pawn->GetCharacterMovement()->IsFalling()) return Fail(TEXT("Land before starting this action."));
    if (Pawn->GetAbilityAnimationDuration(WarAbilities::Motion(A, Pawn->GetAnimationProfile())) <= 0) return Fail(TEXT("Required character animation is missing."));
    FVector Destination; return !bCheckMovement || MovementDestination(A, Target, Destination, Error);
}
bool UWarAbilityRuntime::MovementDestination(const FWarAbilityDefinition& A, AActor* Target, FVector& End, FString& Error, TArray<FVector>* OutPath) const
{
    const auto* Pawn = Avatar(); if (!Pawn) return false; End = Pawn->GetActorLocation();
    if (OutPath) { OutPath->Reset(); OutPath->Add(End); }
    for (const auto& E : A.Effects) if (E.Kind == TEXT("movement"))
    {
        if (const auto* Status = UWarCombatStatus::On(Pawn); Status && Status->Has(TEXT("root")))
        {
            bool bCleanse = false; for (const auto& Effect : A.Effects) bCleanse |= Effect.Cleanse.Contains(TEXT("root"));
            if (!bCleanse) { Error = TEXT("Cannot move while rooted."); return false; }
        }
        FVector Direction = Pawn->GetActorForwardVector(); float Distance = FMath::Clamp(E.Distance, 0.f, 1200.f);
        if (IsValid(Target) && (E.Direction == TEXT("toward_target") || E.Direction == TEXT("backward"))) Direction = (Target->GetActorLocation() - End).GetSafeNormal2D();
        if (E.Direction == TEXT("backward")) Direction *= -1;
        if (E.Direction == TEXT("toward_target") && IsValid(Target)) Distance = FMath::Min(Distance, FMath::Max(0.f, static_cast<float>(FVector::Dist2D(End, Target->GetActorLocation())) - 180.f));
        const auto* Capsule = Pawn->GetCapsuleComponent(); const float Half = Capsule->GetScaledCapsuleHalfHeight();
        FCollisionQueryParams Params(SCENE_QUERY_STAT(WarAbilityTravel), false, Pawn);
        FVector Previous = End;
        // Continuous capsule clearance plus frequent walkable-floor samples prevent wall/ledge traversal.
        for (int32 Step = 1, Steps = FMath::Max(1, FMath::CeilToInt(Distance / 50)); Step <= Steps; ++Step)
        {
            FVector Point = End + Direction * (Distance * Step / Steps); FHitResult Floor, Hit;
            if (!GetWorld()->LineTraceSingleByChannel(Floor, Point + FVector(0,0,40), Point - FVector(0,0,Half + 60), ECC_Visibility, Params)
                || Floor.ImpactNormal.Z < Pawn->GetCharacterMovement()->GetWalkableFloorZ())
            { Error = TEXT("No safe ground along the movement path."); return false; }
            Point.Z = Floor.ImpactPoint.Z + Half + 3;
            if (GetWorld()->SweepSingleByChannel(Hit, Previous, Point, FQuat::Identity, ECC_Pawn,
                FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Half - 2), Params))
            { Error = TEXT("Movement path is obstructed."); return false; }
            Previous = Point;
            if (OutPath) OutPath->Add(Point);
        }
        End = Previous;
    }
    return true;
}
bool UWarAbilityRuntime::TryActivate(FName Id, AActor* Target, FString& Error)
{
    if (!GetOwner()->HasAuthority()) { Error = TEXT("Only the server can activate abilities."); return false; }
    const auto* A = Catalog() ? Catalog()->Find(Id) : nullptr;
    if (!A) { Error = TEXT("Unknown class ability."); return false; }
    if (!CanActivate(*A, Target, Error)) return false;
    FVector End; if (!MovementDestination(*A, Target, End, Error, &MovePath)) return false;
    auto* State = CastChecked<AWarPlayerState>(GetOwner()); auto* Pawn = Avatar();
    Spent = A->bSpendAll ? Resource : A->Cost; Resource = WarAbilities::ResourceAfter(*A, Resource);
    State->GetAbilitySystemComponent()->ApplyModToAttribute(UWarAttributeSet::GetManaAttribute(), EGameplayModOp::Additive, -A->Mana);
    Cooldowns.RemoveAll([&](const auto& C) { return C.Until <= Now() || C.Id == Id; });
    FWarAbilityCooldown Cool; Cool.Id = Id; Cool.Until = Now() + A->Cooldown; Cooldowns.Add(Cool); GcdUntil = Now() + A->Gcd;
    PendingPawn = Pawn; PendingTarget = A->bEnemyTarget ? Target : nullptr; PendingZone = State->GetCurrentZone();
    Casting = Id; bReleased = false; Strength = State->GetEffectiveStrength(); Level = State->GetInventory().CharacterProgression.Level;
    if (A->bEnemyTarget && IsValid(Target)) Pawn->SetActorRotation((Target->GetActorLocation() - Pawn->GetActorLocation()).GetSafeNormal2D().Rotation());
    Origin = Pawn->GetActorLocation(); Facing = Pawn->GetActorForwardVector();
    for (const auto& E : A->Effects) if (E.Kind == TEXT("cleanse")) if (auto* Status = UWarCombatStatus::On(Pawn)) Status->Cleanse(E.Cleanse);
    MoveStart = Origin; MoveEnd = End; MoveAt = Now();
    double Travel = 0; for (int32 Point = 1; Point < MovePath.Num(); ++Point) Travel += FVector::Distance(MovePath[Point - 1], MovePath[Point]);
    MoveUntil = Now() + Travel / 600;
    if (MoveUntil > Now() + .02)
    { BusyUntil = MoveUntil + Pawn->GetAbilityAnimationDuration(WarAbilities::Motion(*A, Pawn->GetAnimationProfile())); ReleaseAt = 0; Pawn->MulticastPlayAbilityMotion(TEXT("run"), MoveUntil - Now(), true); }
    else BeginMotion(*A);
    GetOwner()->ForceNetUpdate(); return true;
}
void UWarAbilityRuntime::BeginMotion(const FWarAbilityDefinition& A)
{
    auto* Pawn = PendingPawn.Get(); if (!Pawn) return;
    const FName Motion = WarAbilities::Motion(A, Pawn->GetAnimationProfile());
    const float Duration = Motion == TEXT("combat_idle") ? 1.2f : Pawn->GetAbilityAnimationDuration(Motion);
    Origin = Pawn->GetActorLocation(); Facing = Pawn->GetActorForwardVector();
    BusyUntil = Now() + Duration; ReleaseAt = Now() + Duration * WarAbilities::ReleaseFraction(A, Pawn->GetAnimationProfile());
    Pawn->MulticastPlayAbilityMotion(Motion, Duration, Motion == TEXT("combat_idle"));
}
void UWarAbilityRuntime::Resolve(const FWarAbilityDefinition& A)
{
    auto* Pawn = PendingPawn.Get(); if (!Pawn) return;
    TArray<AActor*> Targets;
    if (A.Shape == TEXT("area") || A.Shape == TEXT("cone") || A.Shape == TEXT("deployable"))
    {
        const FVector Center = A.bEnemyTarget && PendingTarget.IsValid() ? PendingTarget->GetActorLocation() : Origin;
        for (TActorIterator<APawn> It(GetWorld()); It; ++It)
        {
            const bool bCone = A.Shape == TEXT("cone"); const float Radius = bCone ? A.Range : FMath::Max(100.f, A.Radius);
            if (FVector::DistSquared(Center, It->GetActorLocation()) > FMath::Square(Radius)) continue;
            if (bCone && FVector::DotProduct(Facing, (It->GetActorLocation() - Origin).GetSafeNormal2D()) < .707106f) continue;
            if (Pawn->CanAbilityTarget(*It, A.Range + A.Radius + 100)) Targets.Add(*It);
        }
    }
    else if (Pawn->CanAbilityTarget(PendingTarget.Get(), (A.Shape == TEXT("dash") ? WarValidation::StrikeRangeCm : A.Range) + 25)) Targets.Add(PendingTarget.Get());
    const auto* SourceStatus = UWarCombatStatus::On(Pawn); const float Scale = SourceStatus ? SourceStatus->OutgoingScale() : 1;
    for (const auto& E : A.Effects)
    {
        const float Value = WarAbilities::Amount(E, Strength, Level, Spent, FMath::FRand());
        if (E.Kind == TEXT("heal")) UWarCombatStatus::Heal(Pawn, Value);
        else if (E.Kind == TEXT("player_status")) { if (auto* Status = UWarCombatStatus::On(Pawn)) Status->Apply(E, A.Id, Pawn, Strength, Level); }
        else if (E.Kind == TEXT("damage") || E.Kind == TEXT("status")) for (AActor* Target : Targets)
        {
            if (E.Kind == TEXT("damage")) UWarCombatStatus::Damage(Target, Pawn, Value * Scale, A.Range + A.Radius + 100);
            else if (Pawn->CanAbilityTarget(Target, A.Range + A.Radius + 100)) if (auto* Status = UWarCombatStatus::On(Target)) Status->Apply(E, A.Id, Pawn, Strength, Level);
        }
    }
}
void UWarAbilityRuntime::Cancel()
{
    if (!bReleased && PendingPawn.IsValid()) PendingPawn->MulticastPlayAbilityMotion(TEXT("combat_idle"), 0, true);
    Casting = NAME_None; PendingPawn.Reset(); PendingTarget.Reset(); BusyUntil = 0; MoveUntil = 0; ReleaseAt = 0;
}
void UWarAbilityRuntime::TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta, TickType, Function); if (!GetOwner()->HasAuthority() || Casting.IsNone()) return;
    auto* Pawn = PendingPawn.Get(); auto* State = Cast<AWarPlayerState>(GetOwner()); const auto* A = Catalog() ? Catalog()->Find(Casting) : nullptr;
    const auto* Status = UWarCombatStatus::On(Pawn);
    if (!A || !Pawn || Pawn != Avatar() || Pawn->IsDead() || State->GetCurrentZone() != PendingZone
        || (Status && (Status->Has(TEXT("stagger")) || (A->bBlockedBySilence && Status->Has(TEXT("silence"))) || (MoveUntil > Now() && Status->Has(TEXT("root"))))))
    { Cancel(); return; }
    if (MoveUntil > 0)
    {
        FHitResult Hit; const float Alpha = FMath::Clamp((Now() - MoveAt) / FMath::Max(.001, MoveUntil - MoveAt), 0., 1.);
        // Follow the sampled floor, including slopes and dips, instead of drawing a
        // straight airborne chord between the two endpoints.
        FVector Position = MoveEnd; double Remaining = (Now() - MoveAt) * 600;
        for (int32 Point = 1; Point < MovePath.Num(); ++Point)
        {
            const double Length = FVector::Distance(MovePath[Point - 1], MovePath[Point]);
            if (Remaining <= Length && Length > UE_SMALL_NUMBER)
            { Position = FMath::Lerp(MovePath[Point - 1], MovePath[Point], FMath::Clamp(Remaining / Length, 0., 1.)); break; }
            Remaining -= Length;
        }
        Pawn->SetActorLocation(Position, true, &Hit);
        if (Hit.bBlockingHit || Alpha >= 1) { MoveUntil = 0; BeginMotion(*A); }
        return;
    }
    if (!bReleased && Now() >= ReleaseAt)
    {
        // Projectiles keep their catalog flight time; melee applies at the equipped clip contact.
        if (ReleaseAt > 0 && A->ProjectileSpeed > 0 && PendingTarget.IsValid())
        { ReleaseAt = -Now() - FMath::Min(.8, FVector::Distance(Pawn->GetActorLocation(), PendingTarget->GetActorLocation()) / A->ProjectileSpeed); BusyUntil = FMath::Max(BusyUntil, -ReleaseAt); }
        else if (ReleaseAt >= 0 || Now() >= -ReleaseAt) { Resolve(*A); bReleased = true; }
    }
    if (bReleased && Now() >= BusyUntil) Cancel();
}
void UWarAbilityRuntime::ServerActivate_Implementation(FName Id, AActor* Target)
{
    if (Now() < NextRequest) return; NextRequest = Now() + .1;
    FString Error; if (!TryActivate(Id, Target, Error)) ClientResult(Error);
}
void UWarAbilityRuntime::ClientResult_Implementation(const FString& Message)
{ LastMessage = Message; MessageUntil = Now() + 4; }
FString UWarAbilityRuntime::Description() const
{
    const auto Kit = Catalog() ? Catalog()->Kit(Career) : TArray<const FWarAbilityDefinition*>();
    FString Result = Kit.IsEmpty() ? FString() : FString::Printf(TEXT("%s %.0f / %.0f"), *Kit[0]->ResourceLabel, Resource, Kit[0]->ResourceMax);
    if (IsBusy()) if (const auto* A = Catalog()->Find(Casting)) Result += TEXT("   |   ") + A->Name;
    if (const auto* Status = UWarCombatStatus::On(Avatar())) Result += TEXT("   ") + Status->Description();
    return Result;
}
void UWarAbilityRuntime::RestoreResource()
{ if (GetOwner()->HasAuthority() && Catalog()) { const auto Kit = Catalog()->Kit(Career); if (!Kit.IsEmpty()) Resource = Kit[0]->ResourceMax; GetOwner()->ForceNetUpdate(); } }
void UWarAbilityRuntime::ResetCooldowns()
{ if (GetOwner()->HasAuthority()) { Cooldowns.Reset(); GcdUntil = 0; GetOwner()->ForceNetUpdate(); } }
