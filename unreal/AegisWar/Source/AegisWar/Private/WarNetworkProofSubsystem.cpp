#include "WarNetworkProofSubsystem.h"
#include "AegisWar.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarCraftingStation.h"
#include "WarPlayerController.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "WarQuestRules.h"
#include "WarQuestNpc.h"
#include "Components/CapsuleComponent.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"
#include "AbilitySystemComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
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

void UWarNetworkProofSubsystem::ReportClientReady(AWarPlayerController* Controller)
{
    if (GetWorld()->GetNetMode() == NM_DedicatedServer && IsValid(Controller) && Controller->GetWorld() == GetWorld())
        ReadyControllers.Add(Controller);
}

void UWarNetworkProofSubsystem::GrantClientStart()
{
    if (GetWorld()->GetNetMode() == NM_Client) bStartGranted = true;
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
    Report->SetBoolField(TEXT("remoteGmRejected"), bGmDenied);
    Report->SetBoolField(TEXT("remoteGmCreationRejected"), bGmCreationDenied);
    Report->SetBoolField(TEXT("remoteGmTraversalRejected"), bGmTraversalDenied);
    Report->SetBoolField(TEXT("remoteGmReturnRejected"), bGmReturnDenied);
    Report->SetBoolField(TEXT("remoteGmPlacementRejected"), bGmPlacementDenied);
    Report->SetBoolField(TEXT("remoteGmDropRejected"), bGmDropDenied);
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
    Report->SetBoolField(TEXT("craftingAuthority"), bCraftVerified);
    Report->SetBoolField(TEXT("salvageAuthority"), bSalvageVerified);
    Report->SetBoolField(TEXT("cultivationAuthority"), bCultivationVerified);
    Report->SetBoolField(TEXT("progressionAuthority"), bProgressionVerified);
    Report->SetBoolField(TEXT("respawnPreservesProgression"), bRespawnVerified);
    Report->SetBoolField(TEXT("deathObserved"), bDeathObserved);
    Report->SetBoolField(TEXT("questSnapshotPrivacy"), bQuestPrivacyVerified);
    Report->SetBoolField(TEXT("catalogQuestTransactions"), bQuestPrivacyVerified);
    Report->SetBoolField(TEXT("questNpcAuthority"), bQuestNpcVerified);
    Report->SetBoolField(TEXT("questNpcClientRpc"), bQuestNpcRpcVerified);
    Report->SetBoolField(TEXT("cameraSurvivedRespawn"), bCameraSurvivedRespawn);
    Report->SetBoolField(TEXT("autorunMovement"), bAutorunDriveVerified);
    if (GetWorld()->GetNetMode() == NM_Client && FParse::Param(FCommandLine::Get(), TEXT("WarQuestProofUI")))
    {
        bool bInputRestored = false;
        bool bCameraControls = false;
        if (auto* Controller = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()))
        {
            Controller->ToggleInventory();
            Controller->ToggleQuestLog();
            const bool bBlocked = Controller->IsMoveInputIgnored() && Controller->IsLookInputIgnored() && Controller->bShowMouseCursor;
            if (auto* Character = Cast<AWarCharacter>(Controller->GetPawn()))
            {
                const double Distance = Character->GetCameraDistance();
                const auto Rotation = Controller->GetControlRotation();
                Character->ApplyCameraWheel(100); Character->ApplyCameraOrbit(100, 100);
                bCameraControls = Character->GetCameraDistance() == Distance && Controller->GetControlRotation().Equals(Rotation);
                const bool bWasAutoRunning = Character->IsAutoRunning();
                Character->ToggleAutoRun();
                bCameraControls &= Character->IsAutoRunning() == bWasAutoRunning;
            }
            Controller->ToggleInventory();
            Controller->ToggleQuestLog();
            Controller->ToggleQuestLog();
            bInputRestored = bBlocked && !Controller->IsMoveInputIgnored() && !Controller->IsLookInputIgnored() && !Controller->bShowMouseCursor;
            if (auto* Character = Cast<AWarCharacter>(Controller->GetPawn()))
            {
                const double Distance = Character->GetCameraDistance();
                const auto Rotation = Controller->GetControlRotation();
                Character->ApplyCameraWheel(100);
                bCameraControls &= Character->GetCameraDistance() == Distance + 100;
                Character->ApplyCameraOrbit(10, 10);
                bCameraControls &= !Controller->GetControlRotation().Equals(Rotation);
                Character->ApplyCameraOrbit(-10, -10);
                Character->SetCameraIndoorMode(true);
                bCameraControls &= Character->GetCameraDistance() == 220;
                Character->ApplyCameraWheel(10000);
                bCameraControls &= Character->GetCameraDistance() == 380;
                Character->SetCameraIndoorMode(false);
                bCameraControls &= Character->GetCameraDistance() == Distance + 100 && Controller->GetControlRotation().Equals(Rotation);
                Character->ApplyCameraWheel(-100);
                const auto* Boom = Character->FindComponentByClass<USpringArmComponent>();
                bCameraControls &= Boom && FMath::IsNearlyEqual(double(Boom->TargetArmLength), Distance)
                    && Boom->bDoCollisionTest && Boom->ProbeSize == 35.f;
            }
        }
        Report->SetBoolField(TEXT("questPanelInputRestored"), bInputRestored);
        Report->SetBoolField(TEXT("cameraControls"), bCameraControls);
        Report->SetBoolField(TEXT("passed"), bPassed && bInputRestored && bCameraControls);
    }
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
            if (auto* Controller = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController())) Controller->InteractWithStation();
        if (FParse::Param(FCommandLine::Get(), TEXT("WarQuestProofUI")))
            if (auto* Controller = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController())) Controller->ToggleQuestLog();
        const FString Screenshot = FPaths::Combine(Directory, ResultRole + TEXT(".png"));
        const bool bShowUI = FParse::Param(FCommandLine::Get(), TEXT("WarInventoryProofUI"))
            || FParse::Param(FCommandLine::Get(), TEXT("WarQuestProofUI"));
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
    if (!bServer)
        if (auto* Controller = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()))
        {
            if (!bGmDenialRequested && Controller->GetPawn())
            { Controller->ServerWorldEditHistory(false, 0); bGmDenialRequested = true; }
            bGmDenied |= Controller->GetWorldEditMessage() == TEXT("Open the authorized GM workbench before editing.");
            if (bGmDenied && !bGmCreationRequested)
            {
                Controller->ServerCreateWorldObject(TEXT("aegis_city_house_0"), FTransform::Identity, 0);
                bGmCreationRequested = true;
            }
            bGmCreationDenied |= Controller->GetWorldEditMessage() == TEXT("Creation rejected: Open the authorized GM workbench before editing.");
            if (bGmCreationDenied && !bGmTraversalRequested)
            { Controller->ServerSetDevelopmentTraversal(true, 6.f); bGmTraversalRequested = true; }
            bGmTraversalDenied |= Controller->GetWorldEditMessage() == TEXT("Traversal rejected: Development GM traversal is unavailable for this session.");
            if (bGmTraversalDenied && !bGmReturnRequested)
            { Controller->ServerReturnToDevelopmentSpawn(); bGmReturnRequested = true; }
            bGmReturnDenied |= Controller->GetWorldEditMessage() == TEXT("Return rejected: Development GM traversal is unavailable for this session.");
            if (bGmReturnDenied && !bGmPlacementRequested)
            { Controller->ServerPlaceWorldObject(TEXT("aegis_city_house_0"),100,90,0); bGmPlacementRequested = true; }
            bGmPlacementDenied |= Controller->GetWorldEditMessage() == TEXT("Placement rejected: Open the authorized GM workbench before editing.");
            if (bGmPlacementDenied && !bGmDropRequested)
            { Controller->ServerDropWorldObject(TEXT("aegis_city_house_0"),0); bGmDropRequested = true; }
            bGmDropDenied |= Controller->GetWorldEditMessage() == TEXT("Drop rejected: Open the authorized GM workbench before editing.");
        }
    ResultRole = bServer ? TEXT("server") : TEXT("client-pending");
    // Death unpossesses the pawn immediately, so its PlayerState link is cleared before the next tick.
    if (bProgressionVerified && TrackedDefender.IsValid() && TrackedDefenderState.IsValid())
        bDeathObserved |= TrackedDefender->IsDead() && TrackedDefenderState->GetAttributes()->GetHealth() <= 0.f;
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
    TrackedDefender = Defender; TrackedDefenderState = Riftbound;
    ObservedHealth = Riftbound->GetAttributes()->GetHealth();
    ObservedMana = Aegis->GetAttributes()->GetMana();
    const bool bAttackerClient = !bServer && Attacker->IsLocallyControlled();
    const bool bDefenderClient = !bServer && Defender->IsLocallyControlled();
    if (!bServer && !bAttackerClient && !bDefenderClient) return;
    ResultRole = bServer ? TEXT("server") : bAttackerClient ? TEXT("client-aegis") : TEXT("client-riftbound");
    if (!bStartGranted)
    {
        if (bServer)
        {
            auto* AttackerController = Cast<AWarPlayerController>(Attacker->GetController());
            auto* DefenderController = Cast<AWarPlayerController>(Defender->GetController());
            if (AttackerController && DefenderController && ReadyControllers.Contains(AttackerController) && ReadyControllers.Contains(DefenderController))
            {
                AttackerController->ClientDevelopmentProofStart();
                DefenderController->ClientDevelopmentProofStart();
                bStartGranted = true;
            }
        }
        else if (!bReadySent)
        {
            if (auto* Controller = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()))
            {
                InitialAttackerPosition = Attacker->GetActorLocation();
                Controller->ServerDevelopmentProofReady();
                bReadySent = true;
            }
        }
        if (!bStartGranted)
        {
            if (Now - StartedAt > 75) Finish(false, TEXT("Both clients did not acknowledge loaded character content."));
            return;
        }
    }
    if (bServer)
    {
        for (AWarPlayerState* State : {Aegis, Riftbound})
        {
            if (State->GetInventory().Revision != 0) continue;
            FWarInventoryItem Reward;
            Reward.Key = TEXT("sword_iron"); Reward.Kind = TEXT("weapon");
            Reward.EquipSlot = TEXT("mainHand"); Reward.bHasAffix = true; Reward.StrengthBonus = 7;
            FString Error;
            const FGuid Transaction(1, 2, 3, 4);
            FWarInventoryItem Potion;
            Potion.Key = State == Aegis ? TEXT("potion_mana") : TEXT("potion_health");
            Potion.Kind = TEXT("consumable"); Potion.Quantity = 2;
            if (!State->GrantRewards(Transaction, {Reward, Potion}, Error) || State->GrantRewards(Transaction, {Reward, Potion}, Error))
            { Finish(false, TEXT("Trusted reward receipt deduplication failed.")); return; }
        }
        bInventoryVerified |= Aegis->GetInventory().Revision >= 2 && Riftbound->GetInventory().Revision >= 2
            && Aegis->GetInventory().Equipment.Num() == 1 && Riftbound->GetInventory().Equipment.Num() == 1;
        bConsumableVerified |= Aegis->GetInventory().Revision == 3 && Riftbound->GetInventory().Revision == 3
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
        bInventoryVerified |= Snapshot.Revision >= 2 && Snapshot.Items.Num() == 2
            && Snapshot.Items[0].StrengthBonus == 7 && Snapshot.Equipment.Num() == 1
            && Snapshot.Equipment[0].BagSlot == 0 && Remote->GetInventory().Revision == 0
            && Remote->GetInventory().Items.IsEmpty() && Remote->GetInventory().Equipment.IsEmpty();
        bConsumableVerified |= Snapshot.Revision == 3 && Snapshot.Items.Num() == 2 && Snapshot.Items[1].Quantity == 1;
    }
    bAutonomous = !bServer && (bAttackerClient ? Attacker : Defender)->GetLocalRole() == ROLE_AutonomousProxy;
    if (PairReadyAt < 0)
    {
        if (ObservedHealth < 99.f || (bAttackerClient && ObservedMana < 99.f)) return;
        PairReadyAt = Now;
        if (bServer) InitialAttackerPosition = Attacker->GetActorLocation();
    }
    bMoved |= FVector::Dist2D(InitialAttackerPosition, Attacker->GetActorLocation()) > 50.f;
    bMovementAnimation |= Attacker->GetPlayingAnimation() == TEXT("walk") || Attacker->GetPlayingAnimation() == TEXT("run");
    bStrikeAnimation |= Attacker->GetPlayingAnimation() == TEXT("attack_melee");
    const double Elapsed = Now - PairReadyAt;
    if (bAttackerClient)
    {
        // Startup/shader hitches can consume a fixed time window before several movement frames run.
        // Drive to a measured distance; retain the independent server/observer acceptance threshold.
        bMovementDriveComplete |= FVector::Dist2D(InitialAttackerPosition, Attacker->GetActorLocation()) >= 100.f;
        if (!bAutorunDriveStarted && Elapsed < 5.0)
        {
            auto* Controller = Cast<AWarPlayerController>(Attacker->GetController());
            if (!Controller) { Finish(false, TEXT("Autorun requires the owning player controller.")); return; }
            AttackerCameraYaw = Controller->GetLocalCameraState().Yaw;
            Attacker->ApplyCameraOrbit((90.0 - AttackerCameraYaw) / FMath::RadiansToDegrees(0.005), 0);
            Attacker->ToggleAutoRun();
            bAutorunDriveStarted = Attacker->IsAutoRunning();
        }
        if (bAutorunDriveStarted && Attacker->IsAutoRunning() && (bMovementDriveComplete || Elapsed >= 5.0))
        {
            Attacker->ToggleAutoRun();
            Attacker->ApplyCameraOrbit((AttackerCameraYaw - 90.0) / FMath::RadiansToDegrees(0.005), 0);
            bAutorunDriveVerified = bMovementDriveComplete && !Attacker->IsAutoRunning();
        }
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
    if (bConsumableVerified && Elapsed > 5.0)
    {
        if (bServer)
        {
            for (auto* State : {Aegis, Riftbound})
            {
                if (State->GetInventory().Revision != 3) continue;
                TArray<FWarInventoryItem> Ingredients;
                for (const FName Key : {FName(TEXT("craft_vial_cloudy")),
                    FName(State == Aegis ? TEXT("craft_goldweed") : TEXT("craft_mandrake_root")), FName(TEXT("craft_clear_water"))})
                {
                    FWarInventoryItem Item; Item.Key = Key; Item.Kind = TEXT("misc");
                    Item.Quantity = Ingredients.Num() == 1 ? 2 : 1;
                    Ingredients.Add(Item);
                }
                FString Error;
                if (!State->GrantRewards(FGuid(5, 6, 7, 8), Ingredients, Error))
                { Finish(false, TEXT("Crafting proof ingredient delivery failed.")); return; }
            }
        }
        else
        {
            auto* Local = bAttackerClient ? Aegis : Riftbound;
            if (!bCraftRequested && Local->GetInventory().Revision == 4)
            {
                const FName Recipe = bAttackerClient ? TEXT("apothecary_minor_mana") : TEXT("apothecary_minor_health");
                AWarCraftingStation* Station = nullptr;
                for (TActorIterator<AWarCraftingStation> It(GetWorld()); It; ++It)
                    if (It->CanInteract(Local->GetPawn())) { Station = *It; break; }
                if (!Station) { Finish(false, TEXT("Authored crafting station is not available in interaction range.")); return; }
                Local->ServerCraftRecipe(TEXT("fabricated_recipe"), 4, Station);
                Local->ServerCraftRecipe(Recipe, 4, Station);
                Local->ServerCraftRecipe(Recipe, 4, Station);
                bCraftRequested = true;
            }
        }
        const auto Crafted = [](const AWarPlayerState* State) {
            const auto& Snapshot = State->GetInventory();
            return Snapshot.Revision == 5 && Snapshot.Items.Num() == 2 && Snapshot.Items[1].Quantity == 3
                && Snapshot.Professions.Num() == 1 && Snapshot.Professions[0].Profession == TEXT("apothecary")
                && Snapshot.Professions[0].Xp == 10;
        };
        bCraftVerified |= bServer ? Crafted(Aegis) && Crafted(Riftbound)
            : Crafted(bAttackerClient ? Aegis : Riftbound)
                && (bAttackerClient ? Riftbound : Aegis)->GetInventory().Professions.IsEmpty();
    }
    if (bCraftVerified && Elapsed > 7.0)
    {
        if (!bServer && !bSalvageRequested)
        {
            auto* Local = bAttackerClient ? Aegis : Riftbound;
            if (Local->GetInventory().Revision == 5)
            {
                Local->ServerSalvageItem(5, 0); // Equipped item must survive.
                Local->ServerChangeEquipment(5, 0, false);
                Local->ServerSalvageItem(6, 1); // Consumables cannot be salvaged.
                Local->ServerSalvageItem(6, 0);
                Local->ServerSalvageItem(6, 0); // Repeated request must not duplicate materials or XP.
                bSalvageRequested = true;
            }
        }
        const auto Salvaged = [](const AWarPlayerState* State) {
            const auto& Snapshot = State->GetInventory();
            const auto Quantity = [&Snapshot](const FName Key) {
                int32 Total = 0;
                for (const auto& Item : Snapshot.Items) if (Item.Key == Key) Total += Item.Quantity;
                return Total;
            };
            const auto* Progress = Snapshot.Professions.FindByPredicate([](const auto& Row) { return Row.Profession == TEXT("salvaging"); });
            const auto* Apothecary = Snapshot.Professions.FindByPredicate([](const auto& Row) { return Row.Profession == TEXT("apothecary"); });
            return Snapshot.Revision == 7 && Snapshot.Equipment.IsEmpty() && Snapshot.Items.Num() == 4
                && Quantity(TEXT("sword_iron")) == 0 && Quantity(TEXT("craft_scrap_iron")) == 4
                && Quantity(TEXT("craft_talisman_fragment")) == 1 && Quantity(TEXT("craft_essence_minor")) == 1
                && Quantity(TEXT("potion_health")) + Quantity(TEXT("potion_mana")) == 3
                && Snapshot.Professions.Num() == 2 && Progress && Progress->Xp == 8 && Apothecary && Apothecary->Xp == 10;
        };
        bSalvageVerified |= bServer ? Salvaged(Aegis) && Salvaged(Riftbound)
            : Salvaged(bAttackerClient ? Aegis : Riftbound)
                && (bAttackerClient ? Riftbound : Aegis)->GetInventory().Items.IsEmpty()
                && (bAttackerClient ? Riftbound : Aegis)->GetInventory().Professions.IsEmpty();
    }
    if (bSalvageVerified && Elapsed > 9.0)
    {
        if (bServer)
        {
            for (auto* State : {Aegis, Riftbound})
            {
                if (State->GetInventory().Revision != 7) continue;
                TArray<FWarInventoryItem> Seeds;
                FWarInventoryItem Seed; Seed.Key = State == Aegis ? TEXT("seed_mandrake") : TEXT("seed_goldweed");
                Seed.Kind = TEXT("misc"); Seeds.Add(Seed);
                Seed.Key = TEXT("craft_fertile_soil"); Seeds.Add(Seed);
                FString Error;
                if (!State->GrantRewards(FGuid(9, 10, 11, 12), Seeds, Error))
                { Finish(false, TEXT("Cultivation proof seed delivery failed.")); return; }
            }
        }
        else
        {
            auto* Local = bAttackerClient ? Aegis : Riftbound;
            const auto& Snapshot = Local->GetInventory();
            const auto& Remote = (bAttackerClient ? Riftbound : Aegis)->GetInventory();
            bPlotPrivacyVerified |= Snapshot.Revision == 9 && Snapshot.CultivationPlots.Num() == 1
                && Snapshot.CultivationPlots[0].Additive == TEXT("craft_fertile_soil")
                && Snapshot.CultivationPlots[0].ReadyAtMs - Snapshot.CultivationPlots[0].PlantedAtMs == (bAttackerClient ? 30000 : 45000)
                && Snapshot.Professions.Num() == 2 && Remote.Revision == 0 && Remote.CultivationPlots.IsEmpty();
            if (!bPlantRequested && Snapshot.Revision == 8)
            {
                const FName Seed = bAttackerClient ? TEXT("seed_mandrake") : TEXT("seed_goldweed");
                Local->ServerPlantSeed(TEXT("fabricated_seed"), true, 8);
                Local->ServerPlantSeed(Seed, true, 8);
                Local->ServerPlantSeed(Seed, true, 8);
                bPlantRequested = true;
            }
            if (Snapshot.Revision == 9 && Snapshot.CultivationPlots.Num() == 1)
            {
                const auto& Plot = Snapshot.CultivationPlots[0];
                const int64 UtcMs = (FDateTime::UtcNow() - FDateTime(1970, 1, 1)).GetTicks() / ETimespan::TicksPerMillisecond;
                if (!bEarlyHarvestRequested)
                {
                    Local->ServerHarvestCrop(Plot.Id, 9);
                    bEarlyHarvestRequested = true;
                }
                // Client time only schedules this acceptance request; the production server checks readiness independently.
                if (!bHarvestRequested && UtcMs >= Plot.ReadyAtMs + 500)
                {
                    Local->ServerHarvestCrop(Plot.Id, 9);
                    Local->ServerHarvestCrop(Plot.Id, 9);
                    bHarvestRequested = true;
                }
            }
        }
        const auto Cultivated = [](const AWarPlayerState* State, bool Mandrake) {
            const auto& Snapshot = State->GetInventory();
            const auto* Progress = Snapshot.Professions.FindByPredicate([](const auto& Row) { return Row.Profession == TEXT("cultivation"); });
            int32 Harvested = 0;
            for (const auto& Item : Snapshot.Items)
                if (Item.Key == (Mandrake ? TEXT("craft_mandrake_root") : TEXT("craft_goldweed"))) Harvested += Item.Quantity;
            return Snapshot.Revision == 10 && Snapshot.CultivationPlots.IsEmpty() && Snapshot.Items.Num() == 5
                && Snapshot.Professions.Num() == 3 && Progress && Progress->Xp == (Mandrake ? 8 : 10) && Harvested == 3;
        };
        bCultivationVerified |= bServer ? Cultivated(Aegis, true) && Cultivated(Riftbound, false)
            : bPlotPrivacyVerified && Cultivated(bAttackerClient ? Aegis : Riftbound, bAttackerClient)
                && (bAttackerClient ? Riftbound : Aegis)->GetInventory().CultivationPlots.IsEmpty()
                && (bAttackerClient ? Riftbound : Aegis)->GetInventory().Professions.IsEmpty();
    }
    if (bCultivationVerified && Elapsed > 60.0)
    {
        if (bServer)
        {
            for (auto* State : {Aegis, Riftbound})
            {
                if (State->GetInventory().Revision != 10) continue;
                FString Error; const FGuid Reward(13, 14, 15, 16);
                if (!State->GrantCharacterRewards(Reward, 650, 25, {}, Error)
                    || State->GrantCharacterRewards(Reward, 650, 25, {}, Error))
                { Finish(false, TEXT("Progression reward or duplicate rejection failed.")); return; }
            }
        }
        const auto Advanced = [](const AWarPlayerState* State) {
            const auto& Snapshot = State->GetInventory(); const auto& Progression = Snapshot.CharacterProgression;
            return Snapshot.Revision == 11 && Snapshot.Items.Num() == 5 && Snapshot.Professions.Num() == 3
                && Progression.Level == 3 && Progression.Xp == 0 && Progression.Gold == 25 && Progression.BaseStrength == 14
                && Progression.MaxHealth == 140 && Progression.MaxMana == 120 && State->GetEffectiveStrength() == 14
                && FMath::IsNearlyEqual(State->GetAttributes()->GetHealth(), 140.f)
                && FMath::IsNearlyEqual(State->GetAttributes()->GetMana(), 120.f)
                && FMath::IsNearlyEqual(State->GetAttributes()->GetMaxHealth(), 140.f)
                && FMath::IsNearlyEqual(State->GetAttributes()->GetMaxMana(), 120.f);
        };
        const auto& RemoteProgression = (bAttackerClient ? Riftbound : Aegis)->GetInventory().CharacterProgression;
        bProgressionVerified |= bServer ? Advanced(Aegis) && Advanced(Riftbound)
            : Advanced(bAttackerClient ? Aegis : Riftbound) && RemoteProgression.Level == 1
                && RemoteProgression.Xp == 0 && RemoteProgression.Gold == 0;
    }
    if (bDefenderClient && bProgressionVerified && !bCameraPreparedForRespawn && Elapsed > 60.0)
    {
        Defender->ApplyCameraWheel(200);
        Defender->ApplyCameraOrbit(12, -8);
        DefenderCameraRotation = Defender->GetController()->GetControlRotation();
        bCameraPreparedForRespawn = Defender->GetCameraDistance() == 900;
        if (!bCameraPreparedForRespawn) { Finish(false, TEXT("Camera could not prepare the respawn continuity check.")); return; }
    }
    if (bServer && bProgressionVerified && !bDeathRequested && Elapsed > 62.0)
    {
        DefeatedDefender = Defender;
        auto* System = Defender->GetAbilitySystemComponent();
        for (int32 Hit = 0; Hit < 7; ++Hit)
            System->ApplyGameplayEffectToSelf(GetDefault<UWarStrikeDamageEffect>(), 1.f, System->MakeEffectContext());
        if (!Defender->IsDead() || Riftbound->GetAttributes()->GetHealth() > 0.f)
        { Finish(false, TEXT("Server damage did not enter death state.")); return; }
        bDeathRequested = true;
    }
    bDeathObserved |= bProgressionVerified && Defender->IsDead() && Riftbound->GetAttributes()->GetHealth() <= 0.f;
    const auto& RespawnSnapshot = Riftbound->GetInventory();
    const bool bPrivateRespawnState = (!bServer && !bDefenderClient)
        || (RespawnSnapshot.Revision == 11 && RespawnSnapshot.Items.Num() == 5 && RespawnSnapshot.Professions.Num() == 3
            && RespawnSnapshot.CharacterProgression.Level == 3 && RespawnSnapshot.CharacterProgression.Gold == 25);
    bRespawnVerified |= bDeathObserved && bPrivateRespawnState && !Defender->IsDead() && (!bServer || Defender != DefeatedDefender.Get())
        && FMath::IsNearlyEqual(ObservedHealth, 140.f) && Riftbound->GetAttributes()->GetMaxHealth() == 140.f;
    if (bDefenderClient && bRespawnVerified && bCameraPreparedForRespawn)
    {
        const auto* Boom = Defender->FindComponentByClass<USpringArmComponent>();
        bCameraSurvivedRespawn |= Defender->GetCameraDistance() == 900 && Boom && Boom->TargetArmLength == 900.f
            && Defender->GetController()->GetControlRotation().Equals(DefenderCameraRotation);
    }
    // Keep the respawn observation phase separate from the next inventory revision.
    if (bRespawnVerified && Elapsed > 70.0)
    {
        // Aegis uses placed NPC authority checks; Riftbound uses trusted catalog commands until its models are ready.
        const auto QuestId = [](const AWarPlayerState* State) {
            return State->GetRealm() == EWarRealm::Aegis ? FName(TEXT("dawnline-01-scouting")) : FName(TEXT("cinderfen-01-scouting")); };
        if (bServer)
        {
            const auto* Content = GetWorld()->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
            for (auto* State : {Aegis, Riftbound})
            {
                if (State == Riftbound && !State->GetInventory().Quests.IsEmpty()) continue;
                FWarQuestDefinition Quest; FString Error;
                if (!Content || !Content->GetQuest(QuestId(State), Quest, Error))
                { Finish(false, TEXT("Catalog quest is unavailable.")); return; }
                AWarQuestNpc* Giver = nullptr; AWarQuestNpc* Turnin = nullptr;
                auto* Pawn = Cast<AWarCharacter>(State->GetPawn());
                const bool bNpcCase = State == Aegis;
                if (bNpcCase)
                {
                    for (TActorIterator<AWarQuestNpc> It(GetWorld()); It; ++It)
                    {
                        if (It->NpcId == Quest.GiverNpcId && It->ZoneId == Quest.GiverZoneId) Giver = *It;
                        if (It->NpcId == Quest.TurninNpcId && It->ZoneId == Quest.TurninZoneId) Turnin = *It;
                    }
                    if (!Giver || !Turnin || !Pawn) { Finish(false, TEXT("Authored quest NPC proof placements missing.")); return; }
                    const double Height = Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
                    if (bQuestNpcVerified)
                    {
                        // Acceptance/turn-in must arrive through the owning client's RPC, never a server shortcut.
                        if (State->GetInventory().Revision == 12)
                        {
                            for (int32 Kill = 0; Kill < 4; ++Kill)
                                if (!State->RecordCatalogQuestKillTrusted(Quest.Objectives[0].ZoneId, Quest.Objectives[0].KillTarget, FGuid::NewGuid(), Error))
                                { Finish(false, TEXT("NPC quest kill transaction failed.")); return; }
                            Pawn->SetActorLocation(Turnin->GetActorLocation() + FVector(100, 0, Height));
                        }
                        continue;
                    }
                    Pawn->SetActorLocation(Giver->GetActorLocation() + FVector(400, 0, Height));
                    if (State->InteractQuest(Giver, Quest.Id, false, 11, Error))
                    { Finish(false, TEXT("Quest accepted at excluded four-metre boundary.")); return; }
                    Pawn->SetActorLocation(Turnin->GetActorLocation() + FVector(100, 0, Height));
                    if (State->InteractQuest(Turnin, Quest.Id, false, 11, Error))
                    { Finish(false, TEXT("Wrong NPC accepted quest.")); return; }
                    Pawn->SetActorLocation(Giver->GetActorLocation() + FVector(100, 0, Height));
                    Giver->SetActorHiddenInGame(true);
                    const bool HiddenAccepted = State->InteractQuest(Giver, Quest.Id, false, 11, Error);
                    Giver->SetActorHiddenInGame(false);
                    if (HiddenAccepted || State->InteractQuest(Giver, Quest.Id, false, 10, Error))
                    { Finish(false, TEXT("Hidden NPC or stale revision accepted quest.")); return; }
                    bQuestNpcVerified = true;
                    continue;
                }
                if (!State->AcceptCatalogQuestTrusted(Quest.Id, Quest.GiverZoneId, 11, Error))
                { Finish(false, TEXT("Catalog quest could not be accepted.")); return; }
                for (int32 Kill = 0; Kill < 4; ++Kill)
                    if (!State->RecordCatalogQuestKillTrusted(Quest.Objectives[0].ZoneId, Quest.Objectives[0].KillTarget, FGuid::NewGuid(), Error))
                    { Finish(false, TEXT("Catalog quest kill transaction failed.")); return; }
                if (!State->CompleteCatalogQuestTrusted(Quest.Id, Quest.TurninZoneId, 16, Error)
                    || State->CompleteCatalogQuestTrusted(Quest.Id, Quest.TurninZoneId, 17, Error))
                { Finish(false, TEXT("Catalog quest settlement or retry rejection failed.")); return; }
            }
        }
        if (bAttackerClient)
        {
            AWarQuestNpc* Giver = nullptr; AWarQuestNpc* Turnin = nullptr;
            for (TActorIterator<AWarQuestNpc> It(GetWorld()); It; ++It)
            {
                if (It->NpcId == TEXT("quest-1") && It->ZoneId == TEXT("aegis_capital")) Giver = *It;
                if (It->NpcId == TEXT("brightfen_approach_dispatch") && It->ZoneId == TEXT("brightfen_approach")) Turnin = *It;
            }
            FString Name, Error;
            if (Giver && Turnin && !bQuestAcceptRequested && Aegis->GetInventory().Revision == 11
                && Giver->ResolveInteraction(Attacker, Name, Error))
            {
                Aegis->ServerInteractQuest(nullptr, QuestId(Aegis), false, 11);
                Aegis->ServerInteractQuest(Turnin, QuestId(Aegis), false, 11);
                Aegis->ServerInteractQuest(Giver, QuestId(Aegis), false, 10);
                Aegis->ServerInteractQuest(Giver, QuestId(Aegis), false, 11);
                Aegis->ServerInteractQuest(Giver, QuestId(Aegis), false, 11);
                bQuestAcceptRequested = true;
            }
            if (Giver && Turnin && !bQuestTurnInRequested && Aegis->GetInventory().Revision == 16
                && Turnin->ResolveInteraction(Attacker, Name, Error))
            {
                Aegis->ServerInteractQuest(Giver, QuestId(Aegis), true, 16);
                Aegis->ServerInteractQuest(Turnin, QuestId(Aegis), true, 15);
                Aegis->ServerInteractQuest(Turnin, QuestId(Aegis), true, 16);
                Aegis->ServerInteractQuest(Turnin, QuestId(Aegis), true, 16);
                Aegis->ServerInteractQuest(Turnin, QuestId(Aegis), true, 17);
                bQuestTurnInRequested = true;
            }
        }
        const auto HasQuest = [&](const AWarPlayerState* State) {
            const auto& Snapshot = State->GetInventory();
            const auto* Potion = Snapshot.Items.FindByPredicate([](const auto& Item) { return Item.Key == TEXT("potion_health"); });
            return Snapshot.Revision == 17 && Snapshot.Quests.Num() == 1
                && Snapshot.Quests[0].Id == QuestId(State) && Snapshot.Quests[0].Status == TEXT("completed")
                && Snapshot.Quests[0].Counters.Num() == 1 && Snapshot.Quests[0].GetCount(TEXT("kill-raiders")) == 4
                && Snapshot.CharacterProgression.Level == 3 && Snapshot.CharacterProgression.Xp == 150
                && Snapshot.CharacterProgression.Gold == 33 && Potion
                && Potion->Quantity == (State->GetRealm() == EWarRealm::Aegis ? 3 : 6);
        };
        bQuestPrivacyVerified |= bServer ? HasQuest(Aegis) && HasQuest(Riftbound)
            : HasQuest(bAttackerClient ? Aegis : Riftbound) && (bAttackerClient ? Riftbound : Aegis)->GetInventory().Quests.IsEmpty();
        bQuestNpcRpcVerified |= (bServer && bQuestNpcVerified && HasQuest(Aegis))
            || (bAttackerClient && bQuestAcceptRequested && bQuestTurnInRequested && HasQuest(Aegis));
    }
    if (bCombatVerified && bInventoryVerified && bConsumableVerified && bCraftVerified && bSalvageVerified && bCultivationVerified
        && bProgressionVerified && bRespawnVerified && bQuestPrivacyVerified && Elapsed > 74.0
        && (!bDefenderClient || bCameraSurvivedRespawn)
        && ((!bServer && !bAttackerClient) || bQuestNpcRpcVerified) && FMath::IsNearlyEqual(ObservedHealth, 140.f)
        && ((!bServer && !bAttackerClient) || FMath::IsNearlyEqual(ObservedMana, 120.f)))
    {
        Finish(true, TEXT("Movement, combat, private inventory, consumables, crafting, salvage, cultivation, progression and respawn verified."));
    }
    else if (Elapsed > 80)
    {
        Finish(false, FString::Printf(TEXT("Acceptance timed out; distance=%.1f health=%.1f mana=%.1f moved=%d autonomous=%d attacker=%s defender=%s falling=%d"),
            FVector::Dist(Attacker->GetActorLocation(), Defender->GetActorLocation()), ObservedHealth, ObservedMana, bMoved, bAutonomous,
            *Attacker->GetActorLocation().ToString(), *Defender->GetActorLocation().ToString(), Attacker->GetCharacterMovement()->IsFalling()));
    }
}
