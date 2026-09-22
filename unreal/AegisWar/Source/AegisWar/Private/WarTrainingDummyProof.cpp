#include "WarTrainingDummyProof.h"
#include "WarEnemy.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarZoneStreamingSubsystem.h"
#include "AbilitySystemComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

bool UWarTrainingDummyProof::ShouldCreateSubsystem(UObject* Outer) const
{ return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarTrainingDummyProof")); }
TStatId UWarTrainingDummyProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarTrainingDummyProof, STATGROUP_Tickables); }

void UWarTrainingDummyProof::Finish(bool bPassed, const FString& Detail)
{
    bFinished = true;
    UE_LOG(LogTemp, Display, TEXT("WAR_TRAINING_DUMMY_PROOF passed=%d targets=%d stage=%d capital=%d %s"), bPassed, Checked, Stage, Capital, *Detail);
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("TrainingDummyProof"));
    IFileManager::Get().MakeDirectory(*Directory, true);
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"passed\":%s,\"targets\":%d,\"productionAccepted\":false}"),
        bPassed ? TEXT("true") : TEXT("false"), Checked), *FPaths::Combine(Directory, TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, bPassed ? 0 : 1);
}

void UWarTrainingDummyProof::Tick(float DeltaSeconds)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextStep) return;
    if ((Deadline > 0 && Now > Deadline) || Now > 180) { Finish(false, TEXT("Target verification timed out")); return; }
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* State = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!Pawn || !State || !Pawn->IsVisualReady() || !Streaming) return;
    const FName Zone(Capital == 0 ? TEXT("aegis_capital") : TEXT("riftspire_capital"));
    FString Error;
    if (Stage == 0)
    {
        if (!Streaming->EnsureZone(Zone, Error)) { Finish(false, Error); return; }
        Stage = 1; Deadline = Now + 50; return;
    }
    // Load the test area directly; generic GM portal landings have separate travel proofs.
    if (!Streaming->EnsureZone(Zone, Error)) { Finish(false, Error); return; }
    if (!Streaming->IsZoneReady(Zone))
    {
        FString Reason; Streaming->IsZoneReady(Zone, PC, &Reason);
        UE_LOG(LogTemp, Display, TEXT("WAR_DUMMY_WAIT zone=%s destination=%s reason=%s status=%s"),
            *State->GetCurrentZone().ToString(), *Zone.ToString(), *Reason, *PC->GetZoneTravelStatus());
        NextStep = Now + 2;
        return;
    }
    TArray<AWarEnemy*> Targets;
    for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It)
        if (It->ZoneId == Zone) Targets.Add(*It);
    if (Targets.Num() != 3) { Finish(false, TEXT("Capital does not contain three targets")); return; }
    if (Stage == 1)
    {
        for (auto* Target : Targets)
        {
            if (!Target->IsContentReady() || !Target->GetDefinition().bTrainingDummy || !Target->TrainingMesh->GetStaticMesh()
                || Target->IsDead() || !Target->TrainingMesh->IsVisible() || Target->GetTarget())
            { Finish(false, TEXT("Target model or passive readiness failed")); return; }
            FHitResult Floor; FCollisionQueryParams Query(SCENE_QUERY_STAT(WarDummyProofFloor), false, Pawn);
            Query.AddIgnoredActor(Target);
            const FVector Point = Target->GetHome() + FVector(200, 0, 0);
            if (!GetWorld()->LineTraceSingleByChannel(Floor, Point + FVector(0,0,100), Point - FVector(0,0,300), ECC_Visibility, Query)
                || !Pawn->TeleportTo(Floor.ImpactPoint + FVector(0,0,98), FRotator::ZeroRotator))
            { Finish(false, TEXT("Target has no usable melee approach")); return; }
            Pawn->GetCharacterMovement()->StopMovementImmediately();
            State->SetCurrentZoneTrusted(Zone);
            const auto Before = State->GetInventory();
            const FName Other(Capital == 0 ? TEXT("riftspire_capital") : TEXT("aegis_capital"));
            State->SetCurrentZoneTrusted(Other);
            const bool bCrossZone = Pawn->CanStrikeTarget(Target); State->SetCurrentZoneTrusted(Zone);
            if (bCrossZone || !Pawn->CanStrikeTarget(Target)) { Finish(false, TEXT("Target range/zone validation failed")); return; }
            // The first target in each capital exercises the ordinary ability including its cooldown.
            if (Target == Targets[0] && !bStrikeChecked)
            {
                auto* ASC = State->GetAbilitySystemComponent();
                ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(), State->GetAttributes()->GetMaxMana());
                Pawn->RequestTargetStrike(Target);
                StrikeMana = State->GetAttributes()->GetMana();
                if (Target->GetHealth() != Target->GetDefinition().MaxHealth)
                { Finish(false, TEXT("Strike hit before animation contact")); return; }
                Stage = 3; NextStep = Now + .15; return;
            }
            for (int32 Hit = 0; !Target->IsDead() && Hit < 20; ++Hit)
                if (!Target->ReceiveStrike(Pawn)) { Finish(false, TEXT("Server target damage failed")); return; }
            if (!Target->IsDead() || Target->ReceiveStrike(Pawn) || Target->TrainingMesh->IsVisible() || Target->GetTarget()
                || State->AwardEnemyKillTrusted(Zone, Target->EnemyId, FGuid::NewGuid(), {}, Error)
                || !FWarInventorySnapshot::StaticStruct()->CompareScriptStruct(&Before, &State->GetInventory(), 0))
            { Finish(false, TEXT("Target death, passive behavior or reward suppression failed")); return; }
            ++Checked;
        }
        Stage = 2; NextStep = Now + 1; Deadline = Now + 25; return;
    }
    if (Stage == 2)
    {
        for (const auto* Target : Targets)
        {
            if (Target->IsDead()) return;
            if (Target->GetHealth() != Target->GetDefinition().MaxHealth || !Target->TrainingMesh->IsVisible()
                || Target->GetTarget() || FVector::Dist(Target->GetActorLocation(), Target->GetHome()) > 5)
            { Finish(false, TEXT("Target did not respawn stationary at its original position")); return; }
        }
        if (++Capital == 2) { Finish(true, TEXT("Six exact targets: melee access, damage, cooldown, death, no rewards and respawn passed")); return; }
        Stage = 0; bStrikeChecked = false; Deadline = Now + 50;
    }
    if (Stage == 3)
    {
        Pawn->RequestTargetStrike(Targets[0]);
        if (State->GetAttributes()->GetMana() != StrikeMana || Targets[0]->GetHealth() != Targets[0]->GetDefinition().MaxHealth)
        { Finish(false, TEXT("Strike bypassed windup or cooldown")); return; }
        Stage = 4; NextStep = Now + Pawn->GetAbilityAnimationDuration(TEXT("attack_melee")); return;
    }
    if (Stage == 4)
    {
        if (Targets[0]->GetHealth() != Targets[0]->GetDefinition().MaxHealth - WarValidation::StrikeDamage)
        { Finish(false, TEXT("Delayed ordinary strike failed")); return; }
        bStrikeChecked = true; Stage = 1;
    }
}
