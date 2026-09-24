#include "WarAbilityRuntime.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarSiegeGameMode.h"
#include "WarCombatStatus.h"
#include "WarWrathRelic.h"
#include "WarAbilityExecution.h"
#include "AbilitySystemComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"

namespace
{
    bool SiegeAlly(const AWarCharacter* Source, const AWarCharacter* Target, float Range)
    {
        if (!Source || !Target || Target->IsDead() || !Target->IsVisualReady() || Target->IsDevelopmentFlying() || Source->GetWorld() != Target->GetWorld()) return false;
        const auto* A = Source->GetPlayerState<AWarPlayerState>(); const auto* B = Target->GetPlayerState<AWarPlayerState>();
        if (!A || !B || !A->IsSiegeNormalized() || !B->IsSiegeNormalized() || A->GetRealm() != B->GetRealm()) return false;
        const auto* Unit = Cast<AWarSiegeCharacter>(Target);
        if (Unit && Unit->Unit != EWarSiegeUnit::Participant) return false;
        if (FVector::DistSquared(Source->GetActorLocation(), Target->GetActorLocation()) > FMath::Square(Range)) return false;
        FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeHeal), false, Source);
        return Source == Target || !Source->GetWorld()->LineTraceSingleByChannel(Hit, Source->GetActorLocation(), Target->GetActorLocation(), ECC_Visibility, Query) || Hit.GetActor() == Target;
    }
}

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
    if (State->GetCombatLevel() < A.UnlockLevel) return Fail(FString::Printf(TEXT("Unlocks at level %d."), A.UnlockLevel));
    if (Cooldown(A.Id) > 0 || IsBusy() || Pawn->IsActionPlaying()) return Fail(TEXT("Wait for the current action or cooldown."));
    const auto* Status = UWarCombatStatus::On(Pawn);
    TArray<FName> Cleanses;
    for (const auto& E : A.Effects) Cleanses.Append(E.Cleanse);
    if (Status && ((Status->Has(TEXT("stagger")) && !Cleanses.Contains(TEXT("stagger"))) || (A.bBlockedBySilence && Status->Has(TEXT("silence"))))) return Fail(TEXT("Cannot act while staggered or silenced."));
    if (!State->GetAttributes() || State->GetAttributes()->GetMana() < A.Mana) return Fail(FString::Printf(TEXT("Requires %.0f mana."), A.Mana));
    if (Resource < FMath::Max(A.Cost, A.MinimumResource)) return Fail(FString::Printf(TEXT("Requires %.0f %s."), FMath::Max(A.Cost, A.MinimumResource), *A.ResourceLabel));
    if (A.bEnemyTarget && !Pawn->CanAbilityTarget(Target, A.Range)) return Fail(TEXT("Select a living hostile in range with a clear line of sight."));
    if (A.TargetKind==TEXT("ally") && !WarAbilityExecution::Allied(Pawn,Target,A.Range)) return Fail(TEXT("Select a living ally in the same zone, within range and line of sight."));
    if (State->IsSiegeNormalized() && !A.bEnemyTarget && Target && Target != Pawn
        && A.Effects.ContainsByPredicate([](const auto& E) { return E.Kind == TEXT("heal"); })
        && !SiegeAlly(Pawn, Cast<AWarCharacter>(Target), 2000)) return Fail(TEXT("Select a living allied siege participant within 20 metres and line of sight."));
    if (Pawn->GetCharacterMovement()->IsFalling()) return Fail(TEXT("Land before starting this action."));
    if (A.Effects.ContainsByPredicate([](const auto& E) { return E.Kind == TEXT("wrath_relic"); }))
    { FVector Position; if (!AWarWrathRelic::Placement(Pawn, Position, Error)) return false; }
    const FName PresentationId=WarAbilities::Motion(A,Pawn->GetAnimationProfile());
    if (const auto* Recipe=Pawn->GetAbilityPresentation(PresentationId))
    { for (FName Role : Recipe->VariantRoles) if (Pawn->GetAbilityAnimationDuration(Role)<=0) return Fail(TEXT("Required presentation animation is missing.")); }
    else if (Pawn->GetAbilityAnimationDuration(PresentationId)<=0) return Fail(TEXT("Required character animation is missing."));
    FVector Destination; return !bCheckMovement || MovementDestination(A, Target, Destination, Error);
}
bool UWarAbilityRuntime::MovementDestination(const FWarAbilityDefinition& A, AActor* Target, FVector& End, FString& Error, TArray<FVector>* OutPath) const
{
    const auto* Pawn = Avatar(); if (!Pawn) return false; End = Pawn->GetActorLocation();
    if (OutPath) { OutPath->Reset(); OutPath->Add(End); }
    if (const auto* Recipe = Pawn->GetAbilityPresentation(WarAbilities::Motion(A,Pawn->GetAnimationProfile())); Recipe && Recipe->Movement == TEXT("leap"))
    {
        if (Recipe->CapsuleHeights.Num() < 2) { Error = TEXT("Leap movement has no authored capsule trajectory."); return false; }
        const auto* Capsule = Pawn->GetCapsuleComponent();
        FCollisionQueryParams Query(SCENE_QUERY_STAT(WarLeapClearance),false,Pawn); FVector Previous=End;
        for (float Height : Recipe->CapsuleHeights)
        {
            FHitResult Hit; const FVector Point=End+FVector(0,0,Height);
            if (!FMath::IsFinite(Height) || Height<0 || Height>150
                || GetWorld()->SweepSingleByChannel(Hit,Previous,Point,FQuat::Identity,ECC_Pawn,
                    FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()-2),Query))
            { Error=TEXT("There is not enough overhead clearance for this attack."); return false; }
            Previous=Point;
        }
    }
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
bool UWarAbilityRuntime::TryActivate(FName Id, AActor* Target, FString& Error, const FVector* Ground)
{
    if (!GetOwner()->HasAuthority()) { Error = TEXT("Only the server can activate abilities."); return false; }
    const auto* A = Catalog() ? Catalog()->Find(Id,Career) : nullptr;
    if (!A) { Error = TEXT("Unknown class ability."); return false; }
    if (!CanActivate(*A, Target, Error)) return false;
    if (A->TargetKind==TEXT("ground"))
    {
        if (!Ground || Ground->ContainsNaN() || FVector::DistSquared(Avatar()->GetActorLocation(),*Ground)>FMath::Square(A->Range))
        { Error=TEXT("Select a ground point within range."); return false; }
        FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(AbilityGround),false,Avatar());
        if (!GetWorld()->LineTraceSingleByChannel(Hit,*Ground+FVector(0,0,50),*Ground-FVector(0,0,100),ECC_Visibility,Query))
        { Error=TEXT("Ground targeting requires a loaded surface."); return false; }
        GroundPoint=Hit.ImpactPoint;
        if (GetWorld()->LineTraceSingleByChannel(Hit,Avatar()->GetActorLocation(),GroundPoint+FVector(0,0,5),ECC_Visibility,Query))
        { Error=TEXT("The selected ground point is obstructed."); return false; }
    }
    FVector End; if (!MovementDestination(*A, Target, End, Error, &MovePath)) return false;
    auto* State = CastChecked<AWarPlayerState>(GetOwner()); auto* Pawn = Avatar();
    Activation=MakeShared<const FWarAbilityDefinition>(*A); A=Activation.Get();
    ApplicationConditions.Reset(); ChannelBaselines.Reset();
    if (A->TargetKind==TEXT("self")) Target=Pawn;
    ActivationPresentation.Reset();
    if (const auto* Recipe=Pawn->GetAbilityPresentation(WarAbilities::Motion(*A,Pawn->GetAnimationProfile()))) ActivationPresentation=*Recipe;
    CastConditions=WarAbilityConditions::Evaluate(A->Conditions,TEXT("cast_start"),WarAbilityExecution::Capture(Pawn,Target,Target ? Target : Pawn,Now()));
    RecordConditions(CastConditions.Traces);
    Spent = A->bSpendAll ? Resource : A->Cost; Resource = WarAbilities::ResourceAfter(*A, Resource);
    State->GetAbilitySystemComponent()->ApplyModToAttribute(UWarAttributeSet::GetManaAttribute(), EGameplayModOp::Additive, -A->Mana);
    Cooldowns.RemoveAll([&](const auto& C) { return C.Until <= Now() || C.Id == Id; });
    FWarAbilityCooldown Cool; Cool.Id = Id; Cool.Until = Now() + A->Cooldown; Cooldowns.Add(Cool); GcdUntil = Now() + A->Gcd;
    PendingPawn = Pawn; PendingTarget = A->bEnemyTarget || !A->Conditions.IsEmpty() || A->TargetKind==TEXT("ally") || !A->bLegacyTargeting || (State->IsSiegeNormalized() && !A->bEnemyTarget && A->Effects.ContainsByPredicate([](const auto& E) { return E.Kind == TEXT("heal"); })) ? Target : nullptr; PendingZone = State->GetCurrentZone();
    Casting = Id; bReleased = false; Strength = State->GetEffectiveStrength(); Level = State->GetCombatLevel();
    if (A->bEnemyTarget && IsValid(Target)) Pawn->SetActorRotation((Target->GetActorLocation() - Pawn->GetActorLocation()).GetSafeNormal2D().Rotation());
    Origin = Pawn->GetActorLocation(); Facing = Pawn->GetActorForwardVector();
    for (const auto& E : A->Effects) if (E.Kind == TEXT("cleanse") && (E.Recipient.IsNone() || E.Recipient==TEXT("caster"))) if (auto* Status = UWarCombatStatus::On(Pawn)) Status->Cleanse(E.Cleanse);
    MoveStart = Origin; MoveEnd = End; MoveAt = Now();
    double Travel = 0; for (int32 Point = 1; Point < MovePath.Num(); ++Point) Travel += FVector::Distance(MovePath[Point - 1], MovePath[Point]);
    MoveUntil = Travel > 1 ? Now() + Travel / 600 : 0;
    const auto* Presentation = ActivationPresentation.IsSet() ? &ActivationPresentation.GetValue() : nullptr;
    bMotionDuringTravel = Presentation && Travel > 1 && (Presentation->Movement == TEXT("slide") || Presentation->Movement == TEXT("charge"));
    if (bMotionDuringTravel)
    {
        BeginMotion(*A); MoveAt = Now()+.15; MoveUntil = Now()+FMath::Max(.2f, Presentation->ContactSeconds*.9f);
    }
    else if (MoveUntil > Now() + .02)
    { BusyUntil = MoveUntil + Pawn->GetAbilityAnimationDuration(WarAbilities::Motion(*A, Pawn->GetAnimationProfile())); ReleaseAt = 0; Pawn->MulticastPlayAbilityMotion(TEXT("run"), MoveUntil - Now(), true); }
    else BeginMotion(*A);
    GetOwner()->ForceNetUpdate(); return true;
}
void UWarAbilityRuntime::BeginMotion(const FWarAbilityDefinition& A)
{
    auto* Pawn = PendingPawn.Get(); if (!Pawn) return;
    if (const auto* Presentation = ActivationPresentation.IsSet() ? &ActivationPresentation.GetValue() : nullptr)
    {
        Origin = Pawn->GetActorLocation(); Facing = Pawn->GetActorForwardVector();
        BusyUntil = Now()+Presentation->Duration; ReleaseAt = Now()+Presentation->ContactSeconds;
        if (A.bAuthoredTiming || !A.bLegacyTargeting) { ReleaseAt=Now()+(A.TimingMode==TEXT("instant") ? 0 : A.CastSeconds); BusyUntil=FMath::Max(BusyUntil,ReleaseAt); }
        if (Presentation->Movement == TEXT("leap")) Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
        Pawn->BeginAbilityPresentation(WarAbilities::Motion(A,Pawn->GetAnimationProfile()));
        if (A.TimingMode==TEXT("channel")) { ChannelUntil=ReleaseAt+A.ChannelSeconds; NextChannelTick=ReleaseAt; BusyUntil=FMath::Max(BusyUntil,ChannelUntil); }
        return;
    }
    const FName Motion = WarAbilities::Motion(A, Pawn->GetAnimationProfile());
    const float Duration = Motion == TEXT("combat_idle") ? 1.2f : Pawn->GetAbilityAnimationDuration(Motion);
    Origin = Pawn->GetActorLocation(); Facing = Pawn->GetActorForwardVector();
    BusyUntil = Now() + Duration; ReleaseAt = Now() + Duration * WarAbilities::ReleaseFraction(A, Pawn->GetAnimationProfile());
    if (A.bAuthoredTiming || !A.bLegacyTargeting) { ReleaseAt=Now()+(A.TimingMode==TEXT("instant") ? 0 : A.CastSeconds); BusyUntil=FMath::Max(BusyUntil,ReleaseAt); }
    Pawn->MulticastPlayAbilityMotion(Motion, Duration, Motion == TEXT("combat_idle"));
    if (A.TimingMode==TEXT("channel")) { ChannelUntil=ReleaseAt+A.ChannelSeconds; NextChannelTick=ReleaseAt; BusyUntil=FMath::Max(BusyUntil,ChannelUntil); }
}
void UWarAbilityRuntime::Resolve(const FWarAbilityDefinition& A)
{
    auto* Pawn = PendingPawn.Get(); if (!Pawn) return;
    TArray<AActor*> Targets;
    if (A.Shape == TEXT("area") || A.Shape == TEXT("cone") || A.Shape == TEXT("deployable"))
    {
        const FVector Center = A.TargetKind==TEXT("ground") ? GroundPoint : A.bEnemyTarget && PendingTarget.IsValid() ? PendingTarget->GetActorLocation() : Origin;
        for (TActorIterator<APawn> It(GetWorld()); It; ++It)
        {
            const bool bCone = A.Shape == TEXT("cone"); const float Radius = bCone ? A.Range : FMath::Max(100.f, A.Radius);
            if (FVector::DistSquared(Center, It->GetActorLocation()) > FMath::Square(Radius)) continue;
            if (bCone && FVector::DotProduct(Facing, (It->GetActorLocation() - Origin).GetSafeNormal2D()) < .707106f) continue;
            if (Pawn->CanAbilityTarget(*It, A.Range + A.Radius + 100)) Targets.Add(*It);
        }
    }
    else if (Pawn->CanAbilityTarget(PendingTarget.Get(), (A.Shape == TEXT("dash") ? WarValidation::StrikeRangeCm : A.Range) + 25)) Targets.Add(PendingTarget.Get());
    Targets.Sort([](const AActor& Left,const AActor& Right) { return Left.GetUniqueID()<Right.GetUniqueID(); });
    if (Targets.Num()>A.MaxTargets) Targets.SetNum(A.MaxTargets);
    if (!A.Conditions.IsEmpty() || A.Effects.ContainsByPredicate([](const auto& E) { return E.PeriodicDuration>0 || !E.Recipient.IsNone(); }))
    {
        struct FApplication { AActor* Recipient=nullptr; FWarAbilityEffect Effect; float Amount=0; bool bBonus=false; };
        TArray<FApplication> Applications;
        TMap<AActor*,FWarRuleEvaluation> Evaluations, TickEvaluations;
        const auto Recipients=[&](const FWarAbilityEffect& E) {
            TArray<AActor*> Result;
            const bool Beneficial=E.Kind==TEXT("heal") || E.Kind==TEXT("player_status") || E.Kind==TEXT("cleanse");
            if (E.Recipient==TEXT("caster") || (E.Recipient.IsNone() && Beneficial)) Result.Add(Pawn);
            else if (E.Recipient==TEXT("allies"))
            {
                const FVector Center=A.TargetKind==TEXT("ground") ? GroundPoint : PendingTarget.IsValid() ? PendingTarget->GetActorLocation() : Origin;
                for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
                    if (FVector::DistSquared(Center,It->GetActorLocation())<=FMath::Square(FMath::Max(100.f,A.Radius)) && WarAbilityExecution::Allied(Pawn,*It,A.Range+A.Radius+100)) Result.Add(*It);
            }
            else if (Beneficial)
            { if (A.TargetKind==TEXT("self")) Result.Add(Pawn); else if (PendingTarget.IsValid()) Result.Add(PendingTarget.Get()); }
            else Result=Targets;
            if (A.bLegacyTargeting && E.Kind==TEXT("heal") && !A.bEnemyTarget && PendingTarget.IsValid() && Pawn->GetPlayerState<AWarPlayerState>()->IsSiegeNormalized())
            { Result.Reset(); if (SiegeAlly(Pawn,Cast<AWarCharacter>(PendingTarget.Get()),2000)) Result.Add(PendingTarget.Get()); }
            Result.Sort([](const AActor& Left,const AActor& Right) { return Left.GetUniqueID()<Right.GetUniqueID(); });
            if (Result.Num()>A.MaxTargets) Result.SetNum(A.MaxTargets); return Result;
        };
        TSet<AActor*> Relevant;
        for (const auto& E : A.Effects) for (auto* Recipient : Recipients(E)) Relevant.Add(Recipient);
        // Conditional-only bonuses still get a recipient even for a movement/utility base ability.
        if (Relevant.IsEmpty()) Relevant.Add(PendingTarget.IsValid() ? PendingTarget.Get() : Pawn);
        for (auto* Recipient : Relevant)
        {
            const auto Context=WarAbilityExecution::Capture(Pawn,PendingTarget.Get(),Recipient,Now());
            const TWeakObjectPtr<AActor> Key(Recipient);
            if (const auto* Cached=ApplicationConditions.Find(Key)) Evaluations.Add(Recipient,*Cached);
            else { auto Evaluation=WarAbilityConditions::Evaluate(A.Conditions,TEXT("application"),Context); RecordConditions(Evaluation.Traces); ApplicationConditions.Add(Key,Evaluation); Evaluations.Add(Recipient,MoveTemp(Evaluation)); }
            if (A.TimingMode==TEXT("channel"))
            { auto Tick=WarAbilityConditions::Evaluate(A.Conditions,TEXT("tick"),Context); RecordConditions(Tick.Traces); TickEvaluations.Add(Recipient,MoveTemp(Tick)); }
        }
        for (const auto& E : A.Effects) for (auto* Recipient : Recipients(E))
        {
            const FString BaselineKey=Recipient->GetPathName()+TEXT(":")+E.Id.ToString();
            float Baseline;
            if (const float* Cached=ChannelBaselines.Find(BaselineKey)) Baseline=*Cached;
            else { Baseline=WarAbilityConditions::Amount(WarAbilities::RawAmount(E,Strength,Level,Spent,FMath::FRand()),E.Id,{CastConditions,Evaluations.FindChecked(Recipient)}); ChannelBaselines.Add(BaselineKey,Baseline); }
            float Value=Baseline;
            if (const auto* Tick=TickEvaluations.Find(Recipient)) Value=WarAbilityConditions::Amount(Baseline,E.Id,{*Tick});
            if (E.Kind==TEXT("damage")) if (const auto* Status=UWarCombatStatus::On(Pawn)) Value*=Status->OutgoingScale();
            Applications.Add({Recipient,E,Value,false});
        }
        TSet<FString> Bonuses;
        for (auto* Recipient : Relevant)
        {
            TArray<FWarAbilityEffect> Effects;
            if (!bReleased) { Effects=CastConditions.BonusEffects; Effects.Append(Evaluations.FindChecked(Recipient).BonusEffects); }
            if (const auto* Tick=TickEvaluations.Find(Recipient)) Effects.Append(Tick->BonusEffects);
            for (const auto& E : Effects)
            {
                // A matching recipient qualifies only its own targeted bonus. Caster bonuses are deduplicated.
                AActor* Actual=E.Recipient==TEXT("caster") ? Pawn : Recipient;
                if (E.Recipient==TEXT("allies") && !WarAbilityExecution::Allied(Pawn,Actual,A.Range+A.Radius+100)) continue;
                if (E.Recipient==TEXT("enemies") && !Pawn->CanAbilityTarget(Actual,A.Range+A.Radius+100)) continue;
                const FString Key=Actual->GetPathName()+TEXT(":")+E.Id.ToString(); if (Bonuses.Contains(Key)) continue; Bonuses.Add(Key);
                float Value=WarAbilityConditions::Amount(WarAbilities::RawAmount(E,Strength,Level,Spent,FMath::FRand()),E.Id,{});
                if (E.Kind==TEXT("damage")) if (const auto* Status=UWarCombatStatus::On(Pawn)) Value*=Status->OutgoingScale();
                Applications.Add({Actual,E,Value,true});
            }
        }
        for (const auto& Apply : Applications)
        {
            if (Apply.Effect.Kind==TEXT("wrath_relic")) { FString Error; AWarWrathRelic::Place(Pawn,Error); }
            else WarAbilityExecution::Apply(Apply.Effect,Apply.Amount,Pawn,Apply.Recipient,PendingTarget.Get(),Activation,Strength,Level,Apply.bBonus);
        }
        return;
    }
    const auto* SourceStatus = UWarCombatStatus::On(Pawn); const float Scale = SourceStatus ? SourceStatus->OutgoingScale() : 1;
    for (const auto& E : A.Effects)
    {
        const float Value = WarAbilities::Amount(E, Strength, Level, Spent, FMath::FRand());
        if (E.Kind == TEXT("wrath_relic"))
        { FString Error; if (!AWarWrathRelic::Place(Pawn, Error)) ClientResult(Error); }
        else if (E.Kind == TEXT("heal"))
        {
            auto* Ally = Cast<AWarCharacter>(PendingTarget.Get());
            if (!A.bEnemyTarget && Ally && Ally != Pawn && Pawn->GetPlayerState<AWarPlayerState>()->IsSiegeNormalized())
            { if (SiegeAlly(Pawn, Ally, 2000)) UWarCombatStatus::Heal(Ally, Value); }
            else UWarCombatStatus::Heal(Pawn, Value);
        }
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
    if (auto* Pawn = PendingPawn.Get(); Pawn && !Pawn->IsDead() && !Pawn->IsDevelopmentFlying()
        && Pawn->GetCharacterMovement()->MovementMode == MOVE_Flying)
        Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    if (PendingPawn.IsValid()) PendingPawn->MulticastPlayAbilityMotion(TEXT("combat_idle"), 0, true);
    Casting = NAME_None; PendingPawn.Reset(); PendingTarget.Reset(); BusyUntil = 0; MoveUntil = 0; ReleaseAt = 0;
    Activation.Reset(); ActivationPresentation.Reset(); CastConditions={}; ApplicationConditions.Reset(); ChannelBaselines.Reset(); ChannelUntil=0; NextChannelTick=0;
}
void UWarAbilityRuntime::TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta, TickType, Function); if (!GetOwner()->HasAuthority()) return;
    SynchronizeCatalog(); if (Casting.IsNone()) return;
    const auto Snapshot=Activation;
    auto* Pawn = PendingPawn.Get(); auto* State = Cast<AWarPlayerState>(GetOwner()); const auto* A = Snapshot.Get();
    const auto* Status = UWarCombatStatus::On(Pawn);
    if (!A || !Pawn || Pawn != Avatar() || Pawn->IsDead() || State->GetCurrentZone() != PendingZone
        || (Status && (Status->Has(TEXT("stagger")) || (A->bBlockedBySilence && Status->Has(TEXT("silence"))) || (MoveUntil > Now() && Status->Has(TEXT("root"))))))
    { Cancel(); return; }
    if (const auto* Recipe = ActivationPresentation.IsSet() ? &ActivationPresentation.GetValue() : nullptr; Recipe && Recipe->Movement == TEXT("leap"))
    {
        if (Status && Status->Has(TEXT("root"))) { Cancel(); return; }
        const float Position=FMath::Clamp(static_cast<float>((Now()-(BusyUntil-Recipe->Duration))/Recipe->Duration),0.f,1.f)*(Recipe->CapsuleHeights.Num()-1);
        const int32 Index=FMath::FloorToInt(Position);
        const float Height=FMath::Lerp(Recipe->CapsuleHeights[Index],Recipe->CapsuleHeights[FMath::Min(Index+1,Recipe->CapsuleHeights.Num()-1)],Position-Index);
        FHitResult Hit; Pawn->SetActorLocation(MoveStart+FVector(0,0,Height),true,&Hit);
        if (Hit.bBlockingHit) { Cancel(); return; }
    }
    if (MoveUntil > 0)
    {
        FHitResult Hit; const float Alpha = FMath::Clamp((Now() - MoveAt) / FMath::Max(.001, MoveUntil - MoveAt), 0., 1.);
        // Follow the sampled floor, including slopes and dips, instead of drawing a
        // straight airborne chord between the two endpoints.
        double Total = 0; for (int32 Point = 1; Point < MovePath.Num(); ++Point) Total += FVector::Distance(MovePath[Point-1],MovePath[Point]);
        FVector Position = MoveEnd; double Remaining = Alpha * Total;
        for (int32 Point = 1; Point < MovePath.Num(); ++Point)
        {
            const double Length = FVector::Distance(MovePath[Point - 1], MovePath[Point]);
            if (Remaining <= Length && Length > UE_SMALL_NUMBER)
            { Position = FMath::Lerp(MovePath[Point - 1], MovePath[Point], FMath::Clamp(Remaining / Length, 0., 1.)); break; }
            Remaining -= Length;
        }
        Pawn->SetActorLocation(Position, true, &Hit);
        if (Hit.bBlockingHit) { Cancel(); return; }
        if (Alpha >= 1)
        {
            MoveUntil = 0; Origin = Pawn->GetActorLocation(); Facing = Pawn->GetActorForwardVector();
            if (!bMotionDuringTravel) BeginMotion(*A);
        }
        if (!bMotionDuringTravel || MoveUntil > 0) return;
    }
    if (!bReleased && Now() >= ReleaseAt)
    {
        // Projectiles keep their catalog flight time; melee applies at the equipped clip contact.
        if (ReleaseAt > 0 && A->ProjectileSpeed > 0 && PendingTarget.IsValid())
        { ReleaseAt = -Now() - FMath::Min(.8, FVector::Distance(Pawn->GetActorLocation(), PendingTarget->GetActorLocation()) / A->ProjectileSpeed); BusyUntil = FMath::Max(BusyUntil, -ReleaseAt); }
        else if (ReleaseAt >= 0 || Now() >= -ReleaseAt) { Resolve(*A); if (!Activation) return; bReleased = true; NextChannelTick=Now()+A->TickInterval; }
    }
    if (A->TimingMode==TEXT("channel") && bReleased && NextChannelTick>0)
    {
        if (Now()>=NextChannelTick && NextChannelTick<ChannelUntil) { Resolve(*A); if (!Activation) return; NextChannelTick+=A->TickInterval; }
    }
    if (bReleased && Now() >= BusyUntil) Cancel();
}
void UWarAbilityRuntime::ServerActivate_Implementation(FName Id, AActor* Target)
{
    if (Now() < NextRequest) return; NextRequest = Now() + .1;
    if (Catalog() && Catalog()->GetVersion()!=TEXT("baseline")) { ClientResult(TEXT("Refresh the ability catalog before casting.")); return; }
    FString Error; if (!TryActivate(Id, Target, Error)) ClientResult(Error);
}
void UWarAbilityRuntime::ServerActivateVersioned_Implementation(FName Id,AActor* Target,const FString& Version,FVector Ground)
{
    if (Now()<NextRequest) return; NextRequest=Now()+.1;
    if (!Catalog() || Version!=Catalog()->GetVersion()) { ClientResult(TEXT("Ability catalog changed. Waiting for the current revision before the next cast.")); return; }
    const auto* A=Catalog()->Find(Id,Career); FString Error;
    if (!TryActivate(Id,Target,Error,A && A->TargetKind==TEXT("ground") ? &Ground : nullptr)) ClientResult(Error);
}
void UWarAbilityRuntime::SynchronizeCatalog()
{
    const auto* Current=Catalog(); if (!Current || !Avatar() || !Avatar()->GetController() || Avatar()->IsLocallyControlled()) return;
    if (SentCatalogVersion!=Current->GetVersion() && SendingCatalog.IsEmpty() && !Current->GetActiveDocument().IsEmpty())
    {
        SendingCatalogVersion=Current->GetVersion(); SendingIndex=0;
        const FString& Document=Current->GetActiveDocument();
        for (int32 I=0;I<Document.Len();I+=12000) SendingCatalog.Add(Document.Mid(I,12000));
    }
    if (!SendingCatalog.IsEmpty() && Now()>=NextCatalogChunk)
    {
        ClientCatalogChunk(SendingCatalogVersion,SendingIndex,SendingCatalog.Num(),SendingCatalog[SendingIndex]); NextCatalogChunk=Now()+.1;
        if (++SendingIndex==SendingCatalog.Num()) { SentCatalogVersion=SendingCatalogVersion; SendingCatalog.Reset(); }
    }
}
void UWarAbilityRuntime::ClientCatalogChunk_Implementation(const FString& Version,int32 Index,int32 Count,const FString& Chunk)
{
    if (GetOwner()->HasAuthority() || !Catalog() || Count<1 || Count>667 || Index<0 || Index>=Count || Chunk.Len()>12000 || Version.Len()>120) return;
    if (Index==0) { ReceivingCatalog.Reset(); ReceivingCatalogVersion=Version; ReceivingIndex=0; ReceivingCount=Count; }
    if (ReceivingCatalogVersion!=Version || ReceivingIndex!=Index || ReceivingCount!=Count || ReceivingCatalog.Len()+Chunk.Len()>8000000) { ReceivingCatalog.Reset(); ReceivingCount=0; return; }
    ReceivingCatalog+=Chunk; ++ReceivingIndex;
    if (ReceivingIndex==Count)
    {
        FString Error; if (!Catalog()->StageWorkspace(ReceivingCatalog,Version,Error)) ClientResult_Implementation(TEXT("Catalog refresh rejected: ")+Error);
        ReceivingCatalog.Reset(); ReceivingCount=0;
    }
}
FName UWarAbilityRuntime::GetActionState() const
{
    if (Casting.IsNone() || !Activation) return NAME_None;
    if (Activation->TimingMode==TEXT("channel") && ChannelUntil>Now() && bReleased) return TEXT("channeling");
    return bReleased || ReleaseAt<0 || (ReleaseAt>0 && Now()>=ReleaseAt) ? FName(TEXT("recovery")) : FName(TEXT("casting"));
}
void UWarAbilityRuntime::RecordConditions(const TArray<FWarRuleTrace>& Traces)
{ ConditionTraces.Append(Traces); if (ConditionTraces.Num()>512) ConditionTraces.RemoveAt(0,ConditionTraces.Num()-512); }
void UWarAbilityRuntime::ClientResult_Implementation(const FString& Message)
{ LastMessage = Message; MessageUntil = Now() + 4; }
FString UWarAbilityRuntime::Description() const
{
    const auto Kit = Catalog() ? Catalog()->Kit(Career) : TArray<const FWarAbilityDefinition*>();
    FString Result = Kit.IsEmpty() ? FString() : FString::Printf(TEXT("%s %.0f / %.0f"), *Kit[0]->ResourceLabel, Resource, Kit[0]->ResourceMax);
    if (IsBusy() && Activation) Result += TEXT("   |   ") + Activation->Name;
    if (const auto* Status = UWarCombatStatus::On(Avatar())) Result += TEXT("   ") + Status->Description();
    return Result;
}
void UWarAbilityRuntime::RestoreResource()
{ if (GetOwner()->HasAuthority() && Catalog()) { const auto Kit = Catalog()->Kit(Career); if (!Kit.IsEmpty()) Resource = Kit[0]->ResourceMax; GetOwner()->ForceNetUpdate(); } }
void UWarAbilityRuntime::ResetCooldowns()
{ if (GetOwner()->HasAuthority()) { Cooldowns.Reset(); GcdUntil = 0; GetOwner()->ForceNetUpdate(); } }
