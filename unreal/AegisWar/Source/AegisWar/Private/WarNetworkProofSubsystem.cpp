#include "WarNetworkProofSubsystem.h"
#include "AegisWar.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarAttributeSet.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "TimerManager.h"

bool UWarNetworkProofSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(), TEXT("WarNetworkProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking"));
#endif
}

bool UWarNetworkProofSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game;
}

TStatId UWarNetworkProofSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UWarNetworkProofSubsystem, STATGROUP_Tickables);
}

void UWarNetworkProofSubsystem::Finish(const bool bPassed, const FString& Detail)
{
    bFinished = true;
    FString Run;
    FParse::Value(FCommandLine::Get(), TEXT("WarProofRun="), Run);
    if (Run.IsEmpty() || Run.Contains(TEXT("..")) || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\"))) return;
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("NetworkProof"), Run);
    IFileManager::Get().MakeDirectory(*Directory, true);
    const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"), 1);
    Report->SetBoolField(TEXT("passed"), bPassed);
    Report->SetStringField(TEXT("role"), ResultRole);
    Report->SetStringField(TEXT("detail"), Detail);
    Report->SetBoolField(TEXT("observedReplicatedMovement"), bMoved);
    Report->SetBoolField(TEXT("autonomousProxy"), bAutonomous);
    Report->SetBoolField(TEXT("movementAnimation"), bMovementAnimation);
    Report->SetBoolField(TEXT("strikeAnimation"), bStrikeAnimation);
    Report->SetNumberField(TEXT("defenderHealth"), ObservedHealth);
    Report->SetNumberField(TEXT("attackerMana"), ObservedMana);
    Report->SetNumberField(TEXT("strikeRequests"), StrikeRequests);
    Report->SetBoolField(TEXT("graphicalAcceptance"), false);
    Report->SetBoolField(TEXT("inventoryAuthorityAndPrivacy"), bInventoryVerified);
    Report->SetBoolField(TEXT("combatBeforeHealing"), bCombatVerified);
    Report->SetBoolField(TEXT("consumableAuthority"), bConsumableVerified);
    FString Json;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    const FString Filename = FPaths::Combine(Directory, ResultRole + TEXT(".json"));
    if (!FFileHelper::SaveStringToFile(Json, *Filename))
    {
        UE_LOG(LogAegisWar, Error, TEXT("Could not save network proof: %s"), *Filename);
        return;
    }
    UE_LOG(LogAegisWar, Display, TEXT("WAR_NETWORK_PROOF %s passed=%d %s"), *ResultRole, bPassed, *Detail);
    if (GetWorld()->GetNetMode() == NM_Client && FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot")))
    {
        if (FParse::Param(FCommandLine::Get(), TEXT("WarInventoryProofUI")))
            if (auto* Controller = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController())) Controller->ToggleInventory();
        const FString Screenshot = FPaths::Combine(Directory, ResultRole + TEXT(".png"));
        const bool bShowUI = FParse::Param(FCommandLine::Get(), TEXT("WarInventoryProofUI"));
        FTimerHandle CaptureTimer;
        GetWorld()->GetTimerManager().SetTimer(CaptureTimer, [Screenshot, bShowUI] {
            FScreenshotRequest::RequestScreenshot(Screenshot, bShowUI, false);
        }, 0.3f, false);
    }
}

void UWarNetworkProofSubsystem::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (StartedAt < 0) StartedAt = Now;
    const bool bServer = GetWorld()->GetNetMode() == NM_DedicatedServer;
    ResultRole = bServer ? TEXT("server") : TEXT("client-pending");
    AWarCharacter* Attacker = nullptr;
    AWarCharacter* Defender = nullptr;
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
    {
        const AWarPlayerState* State = It->GetPlayerState<AWarPlayerState>();
        if (!State || !It->IsVisualReady() || !It->GetMesh()->GetSkeletalMeshAsset()) continue;
        if (State->GetRealm() == EWarRealm::Aegis) Attacker = *It;
        if (State->GetRealm() == EWarRealm::Riftbound) Defender = *It;
    }
    if (!Attacker || !Defender)
    {
        if (Now - StartedAt > 75) Finish(false, TEXT("Two replicated authored characters did not become ready."));
        return;
    }
    AWarPlayerState* Aegis = Attacker->GetPlayerState<AWarPlayerState>();
    AWarPlayerState* Riftbound = Defender->GetPlayerState<AWarPlayerState>();
    ObservedHealth = Riftbound->GetAttributes()->GetHealth();
    ObservedMana = Aegis->GetAttributes()->GetMana();
    const bool bAttackerClient = !bServer && Attacker->IsLocallyControlled();
    const bool bDefenderClient = !bServer && Defender->IsLocallyControlled();
    if (!bServer && !bAttackerClient && !bDefenderClient) return;
    ResultRole = bServer ? TEXT("server") : bAttackerClient ? TEXT("client-aegis") : TEXT("client-riftbound");
    if (bServer)
    {
        for (AWarPlayerState* State : {Aegis, Riftbound})
        {
            if (State->GetInventory().Revision != 0) continue;
            FWarInventoryItem Reward;
            Reward.Key = TEXT("network_proof_blade"); Reward.Kind = TEXT("weapon");
            Reward.EquipSlot = TEXT("mainHand"); Reward.bHasAffix = true; Reward.StrengthBonus = 7;
            FString Error;
            const FGuid Transaction(1, 2, 3, 4);
            FWarInventoryItem Potion;
            Potion.Key = State == Aegis ? TEXT("potion_mana") : TEXT("potion_health");
            Potion.Kind = TEXT("consumable"); Potion.Quantity = 2;
            if (!State->GrantRewards(Transaction, {Reward, Potion}, Error) || State->GrantRewards(Transaction, {Reward, Potion}, Error))
            { Finish(false, TEXT("Trusted reward receipt deduplication failed.")); return; }
        }
        bInventoryVerified = Aegis->GetInventory().Revision >= 2 && Riftbound->GetInventory().Revision >= 2
            && Aegis->GetInventory().Equipment.Num() == 1 && Riftbound->GetInventory().Equipment.Num() == 1;
        bConsumableVerified = Aegis->GetInventory().Revision == 3 && Riftbound->GetInventory().Revision == 3
            && Aegis->GetInventory().Items.Num() == 2 && Riftbound->GetInventory().Items.Num() == 2
            && Aegis->GetInventory().Items[1].Quantity == 1 && Riftbound->GetInventory().Items[1].Quantity == 1;
    }
    else
    {
        AWarPlayerState* Local = bAttackerClient ? Aegis : Riftbound;
        const AWarPlayerState* Remote = bAttackerClient ? Riftbound : Aegis;
        const auto& Snapshot = Local->GetInventory();
        if (!bInventoryRequestsSent && Snapshot.Revision == 1)
        {
            Local->ServerChangeEquipment(1, 23, true); // Fabricated bag selection must not advance revision.
            Local->ServerChangeEquipment(1, 0, true);
            Local->ServerChangeEquipment(1, 0, false); // Stale revision must not undo the accepted equip.
            bInventoryRequestsSent = true;
        }
        bInventoryVerified = Snapshot.Revision >= 2 && Snapshot.Items.Num() == 2
            && Snapshot.Items[0].StrengthBonus == 7 && Snapshot.Equipment.Num() == 1
            && Snapshot.Equipment[0].BagSlot == 0 && Remote->GetInventory().Revision == 0
            && Remote->GetInventory().Items.IsEmpty() && Remote->GetInventory().Equipment.IsEmpty();
        bConsumableVerified = Snapshot.Revision == 3 && Snapshot.Items.Num() == 2 && Snapshot.Items[1].Quantity == 1;
    }
    bAutonomous = !bServer && (bAttackerClient ? Attacker : Defender)->GetLocalRole() == ROLE_AutonomousProxy;
    if (PairReadyAt < 0)
    {
        if (ObservedHealth < 99.f || (bAttackerClient && ObservedMana < 99.f)) return;
        PairReadyAt = Now;
        InitialAttackerPosition = Attacker->GetActorLocation();
    }
    bMoved |= FVector::Dist2D(InitialAttackerPosition, Attacker->GetActorLocation()) > 50.f;
    bMovementAnimation |= Attacker->GetPlayingAnimation() == TEXT("walk") || Attacker->GetPlayingAnimation() == TEXT("run");
    bStrikeAnimation |= Attacker->GetPlayingAnimation() == TEXT("attack_melee");
    const double Elapsed = Now - PairReadyAt;
    if (bAttackerClient)
    {
        if (Elapsed < 0.35) Attacker->AddMovementInput(FVector(0, 1, 0));
        if ((StrikeRequests == 0 && Elapsed > 1.0) || (StrikeRequests == 1 && Elapsed > 1.3))
        {
            Attacker->RequestTargetStrike(Defender);
            ++StrikeRequests;
        }
    }
    if (Elapsed > 2.0 && bMoved && bInventoryVerified && FMath::IsNearlyEqual(ObservedHealth, 80.f)
        && ((!bServer && !bAttackerClient) || FMath::IsNearlyEqual(ObservedMana, 90.f))
        && (bServer || (bAutonomous && bMovementAnimation && bStrikeAnimation)))
        bCombatVerified = true;
    if (!bServer && bCombatVerified && !bConsumableRequested && Elapsed > 3.0)
    {
        AWarPlayerState* Local = bAttackerClient ? Aegis : Riftbound;
        Local->ServerUseConsumable(2, 0); // Equipment is not consumable.
        Local->ServerUseConsumable(2, 1);
        Local->ServerUseConsumable(2, 1); // Duplicate revision must not consume the second potion.
        bConsumableRequested = true;
    }
    if (bCombatVerified && bInventoryVerified && bConsumableVerified && FMath::IsNearlyEqual(ObservedHealth, 100.f)
        && ((!bServer && !bAttackerClient) || FMath::IsNearlyEqual(ObservedMana, 100.f)))
    {
        Finish(true, TEXT("Movement, combat, private inventory, equipment revision checks and authoritative consumable use verified."));
    }
    else if (Elapsed > 20)
    {
        Finish(false, FString::Printf(TEXT("Acceptance timed out; distance=%.1f health=%.1f mana=%.1f moved=%d autonomous=%d attacker=%s defender=%s falling=%d"),
            FVector::Dist(Attacker->GetActorLocation(), Defender->GetActorLocation()), ObservedHealth, ObservedMana, bMoved, bAutonomous,
            *Attacker->GetActorLocation().ToString(), *Defender->GetActorLocation().ToString(), Attacker->GetCharacterMovement()->IsFalling()));
    }
}
