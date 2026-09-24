#include "WarAbilityProof.h"
#include "WarAbilityCatalog.h"
#include "WarAbilityRuntime.h"
#include "WarCombatStatus.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarEnemy.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

bool UWarAbilityProof::ShouldCreateSubsystem(UObject* Outer) const
{ return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarAbilityProof")); }
TStatId UWarAbilityProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarAbilityProof, STATGROUP_Tickables); }
void UWarAbilityProof::Finish(bool bPassed, const FString& Detail)
{
    bFinished = true;
    UE_LOG(LogTemp, Display, TEXT("WAR_ABILITY_PROOF passed=%d checked=%d index=%d %s"), bPassed, Checked, Index, *Detail);
    auto Json = MakeShared<FJsonObject>(); Json->SetBoolField(TEXT("passed"), bPassed); Json->SetNumberField(TEXT("abilitiesChecked"), Checked);
    Json->SetStringField(TEXT("detail"), Detail); Json->SetBoolField(TEXT("graphicalAcceptance"), false);
    FString Text; FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("AbilityProof")); IFileManager::Get().MakeDirectory(*Directory, true);
    FFileHelper::SaveStringToFile(Text, *FPaths::Combine(Directory, TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, bPassed ? 0 : 1);
}
void UWarAbilityProof::Tick(float DeltaSeconds)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds(); if (Now < Next) return;
    if (Now > 300) { Finish(false, TEXT("Timed out waiting for live ability integration")); return; }
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr; auto* State = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Pawn || !State || !Pawn->IsVisualReady()) return;
    auto* Runtime = State->GetClassAbilities(); auto* Catalog = GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    const auto Kit = Catalog->Kit(Pawn->GetCareerId()); FString Error;
    // Keep the low-health dummy alive for two ticks and the following interrupt check at level 45.
    const float ProofBurnMagnitude = FParse::Param(FCommandLine::Get(), TEXT("WarGmLevelProof")) ? .01f : .15f;
    if (Kit.Num() != 10 || Runtime->GetCareer() != TEXT("battle_prelate")) { Finish(false, TEXT("Prelate class kit not initialized")); return; }
    if (Stage == 4)
    {
        const auto* Target = TestTarget.Get();
        const float TickDamage = FMath::Max(1.f, FMath::RoundToFloat(State->GetEffectiveStrength() * ProofBurnMagnitude + State->GetInventory().CharacterProgression.Level * .5f));
        if (!Target || Target->GetHealth() != TargetHealth - 2 * TickDamage || UWarCombatStatus::On(Target)->Has(TEXT("burn")))
        { Finish(false, TEXT("Periodic damage refresh, tick count or expiry failed")); return; }
        Runtime->ResetCooldowns(); Runtime->RestoreResource();
        TargetHealth = Target->GetHealth(); PlayerHealth = State->GetAttributes()->GetHealth();
        if (!Runtime->TryActivate(Kit[1]->Id, TestTarget.Get(), Error)) { Finish(false, TEXT("Interrupted-cast setup: ") + Error); return; }
        FWarAbilityEffect Stagger; Stagger.StatusKind = TEXT("stagger"); Stagger.Duration = .3f;
        UWarCombatStatus::On(Pawn)->Apply(Stagger, TEXT("proof_interrupt"), Pawn, 10, 1);
        Stage = 5; Next = Now + 2; return;
    }
    if (Stage == 5)
    {
        if (!TestTarget.IsValid() || TestTarget->GetHealth() != TargetHealth || State->GetAttributes()->GetHealth() != PlayerHealth
            || Runtime->IsBusy() || Runtime->Cooldown(Kit[1]->Id) <= 0)
        { Finish(false, TEXT("Interrupted cast applied an effect or refunded its cooldown")); return; }
        Finish(true, TEXT("Ten hotbar entries and live Prelate abilities, level/class/zone rejection, costs, cooldowns, contact timing, periodic damage and interruption verified")); return;
    }
    if (Stage == 0)
    {
        for (int32 Slot = 0; Slot < 10; ++Slot)
            if (PC->GetActionSlot(Slot) != Kit[Slot]->Id || PC->GetActionSlotView(Slot).Label != Kit[Slot]->Name)
            { Finish(false, TEXT("Fresh action bar did not expose all ten named class abilities")); return; }
        if (Runtime->TryActivate(Kit[2]->Id, nullptr, Error) || !Error.Contains(TEXT("level"))) { Finish(false, TEXT("Locked ability accepted at level one")); return; }
        if (Runtime->TryActivate(TEXT("ember_arcanist.spark_lash"), nullptr, Error)) { Finish(false, TEXT("Foreign career ability accepted")); return; }
        if (FParse::Param(FCommandLine::Get(), TEXT("WarGmLevelProof")))
        {
            const auto Before = State->GetInventory();
            PC->ServerGmSetLevel(0); PC->ServerGmSetLevel(46);
            if (State->GetInventory().Revision != Before.Revision)
            { Finish(false, TEXT("Invalid GM levels changed progression")); return; }
            PC->ServerGmSetLevel(45);
            if (State->GetInventory().CharacterProgression.Level != 45 || State->GetAttributes()->GetHealth() != 980
                || State->GetAttributes()->GetMana() != 540 || State->GetEffectiveStrength() != 98)
            { Finish(false, TEXT("GM level 45 did not update progression and GAS")); return; }
            PC->ServerGmSetLevel(1);
            if (State->GetInventory().CharacterProgression.Level != 1 || State->GetAttributes()->GetHealth() != 100
                || Runtime->TryActivate(Kit[2]->Id, nullptr, Error) || !Error.Contains(TEXT("level")))
            { Finish(false, TEXT("Lowering GM level did not restore stats and lock abilities")); return; }
            PC->ServerGmSetLevel(45);
            if (State->GetInventory().CharacterProgression.Level != 45)
            { Finish(false, TEXT("GM could not restore level 45")); return; }
            UE_LOG(LogTemp, Display, TEXT("WAR_GM_LEVEL_PROOF bounds, level 45, GAS stats and level-one ability relock passed"));
        }
        while (State->GetInventory().CharacterProgression.Level < 8)
            if (!State->GrantCharacterRewards(FGuid::NewGuid(), WarProgression::XpForLevel(State->GetInventory().CharacterProgression.Level), 0, {}, Error))
            { Finish(false, Error); return; }
        Stage = 1; Next = Now + .5; return;
    }
    if (Stage == 1)
    {
        if (Index == Kit.Num())
        {
            for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It) if (It->GetDefinition().bTrainingDummy && Pawn->CanAbilityTarget(*It, 300))
            {
                TestTarget = *It; TargetHealth = It->GetHealth();
                FWarAbilityEffect Burn; Burn.StatusId = TEXT("burn"); Burn.StatusKind = TEXT("burn"); Burn.Duration = 2.1f; Burn.Magnitude = ProofBurnMagnitude;
                auto* Status = UWarCombatStatus::On(*It); Status->Clear();
                Status->Apply(Burn, TEXT("proof_burn"), Pawn, State->GetEffectiveStrength(), State->GetInventory().CharacterProgression.Level);
                Status->Apply(Burn, TEXT("proof_burn"), Pawn, State->GetEffectiveStrength(), State->GetInventory().CharacterProgression.Level);
                Stage = 4; Next = Now + 2.3; return;
            }
            Next = Now + .2; return; // Wait for the dummy's existing respawn service.
        }
        const auto& A = *Kit[Index];
        if (!A.UnavailableReason.IsEmpty())
        { if (Runtime->TryActivate(A.Id, nullptr, Error)) { Finish(false, TEXT("Unavailable summon activated")); return; } ++Index; return; }
        AWarEnemy* Target = nullptr;
        for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It) if (It->ZoneId == State->GetCurrentZone() && It->IsContentReady() && It->GetDefinition().bTrainingDummy && !It->IsDead()
            && (!Target || It->GetHealth() > Target->GetHealth())) Target = *It;
        if (!Target) return;
        FHitResult Floor; FCollisionQueryParams Params(SCENE_QUERY_STAT(WarAbilityProofFloor), false, Pawn); Params.AddIgnoredActor(Target);
        const FVector Position = Target->GetActorLocation() + FVector(Index == 3 ? 750 : 210, 0, 0);
        if (!GetWorld()->LineTraceSingleByChannel(Floor, Position + FVector(0,0,200), Position - FVector(0,0,300), ECC_Visibility, Params)
            || !Pawn->TeleportTo(Floor.ImpactPoint + FVector(0,0,98), FRotator(0,180,0))) { Finish(false, TEXT("No safe approach to capital training dummy")); return; }
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        Runtime->ResetCooldowns(); Runtime->RestoreResource(); UWarCombatStatus::On(Pawn)->Clear();
        State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(), State->GetAttributes()->GetMaxMana());
        State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), State->GetAttributes()->GetMaxHealth() / 2);
        TestTarget = Target; ActiveAbility = A.Id; Next = Now + .2; Stage = 2; return;
    }
    const auto* A = Catalog->Find(ActiveAbility); auto* Target = TestTarget.Get();
    if (!A || !Target) { Finish(false, TEXT("Proof lost catalog or dummy")); return; }
    if (Stage == 2)
    {
        TargetHealth = Target->GetHealth(); PlayerHealth = State->GetAttributes()->GetHealth(); ResourceBefore = Runtime->GetResource();
        const float ManaBefore = State->GetAttributes()->GetMana();
        const FName Motion = WarAbilities::Motion(*A, Pawn->GetAnimationProfile());
        const auto* Presentation = Pawn->GetAbilityPresentation(A->Id);
        ImpactNotBefore = Now + (Presentation ? Presentation->ContactSeconds : Pawn->GetAbilityAnimationDuration(Motion) * WarAbilities::ReleaseFraction(*A, Pawn->GetAnimationProfile())) - .02;
        const FName Zone = State->GetCurrentZone(); State->SetCurrentZoneTrusted(TEXT("riftspire_capital"));
        const bool WrongZone = A->bEnemyTarget && Runtime->TryActivate(A->Id, Target, Error); State->SetCurrentZoneTrusted(Zone);
        if (WrongZone) { Finish(false, TEXT("Cross-zone cast accepted")); return; }
        if (!Runtime->TryActivate(A->Id, Target, Error)) { Finish(false, A->Name + TEXT(": ") + Error); return; }
        if (Target->GetHealth() != TargetHealth || State->GetAttributes()->GetHealth() != PlayerHealth)
        { Finish(false, TEXT("Effect applied before its animation contact")); return; }
        if (!FMath::IsNearlyEqual(State->GetAttributes()->GetMana(), ManaBefore - A->Mana)
            || !FMath::IsNearlyEqual(Runtime->GetResource(), WarAbilities::ResourceAfter(*A, ResourceBefore))) { Finish(false, TEXT("Ability costs/resource build incorrect")); return; }
        if (Runtime->TryActivate(A->Id, Target, Error)) { Finish(false, TEXT("Duplicate cast bypassed action/cooldown")); return; }
        if (FParse::Param(FCommandLine::Get(), TEXT("WarGmLevelProof")))
        {
            const int32 Revision = State->GetInventory().Revision;
            PC->ServerGmSetLevel(1);
            if (State->GetInventory().CharacterProgression.Level != 45 || State->GetInventory().Revision != Revision)
            { Finish(false, TEXT("GM level changed during an active ability")); return; }
        }
        Stage = 3; Next = Now + .15; return;
    }
    if (Stage == 3)
    {
        if (Now < ImpactNotBefore && (Target->GetHealth() != TargetHealth || State->GetAttributes()->GetHealth() != PlayerHealth))
        { Finish(false, TEXT("Impact occurred during the supplied hammer's backswing")); return; }
        if (Runtime->IsBusy()) { Next = Now + .1; return; }
        for (const auto& E : A->Effects)
        {
            if (E.Kind == TEXT("damage") && Target->GetHealth() >= TargetHealth) { Finish(false, A->Name + TEXT(" did not damage the dummy")); return; }
            if (E.Kind == TEXT("heal") && State->GetAttributes()->GetHealth() <= PlayerHealth) { Finish(false, A->Name + TEXT(" did not heal")); return; }
            if (E.Kind == TEXT("player_status") && !UWarCombatStatus::On(Pawn)->Has(E.StatusKind)) { Finish(false, A->Name + TEXT(" did not apply its buff")); return; }
            if (E.Kind == TEXT("movement") && FVector::Dist2D(Pawn->GetActorLocation(), Target->GetActorLocation()) > 230) { Finish(false, TEXT("Penance did not complete its swept approach")); return; }
        }
        UE_LOG(LogTemp, Display, TEXT("WAR_ABILITY_VERIFIED %s mana=%.0f resource=%.0f health=%.0f target=%.0f"), *A->Id.ToString(), State->GetAttributes()->GetMana(), Runtime->GetResource(), State->GetAttributes()->GetHealth(), Target->GetHealth());
        ++Checked; ++Index; Stage = 1; Next = Now + .1;
    }
}
