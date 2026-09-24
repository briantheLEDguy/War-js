#include "WarGameMode.h"
#include "AegisWar.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarRuntimeSettings.h"
#include "WarTypes.h"
#include "WarQuestNpc.h"
#include "WarQuestHud.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "TimerManager.h"

AWarGameMode::AWarGameMode()
{
    DefaultPawnClass = AWarCharacter::StaticClass();
    PlayerStateClass = AWarPlayerState::StaticClass();
    PlayerControllerClass = AWarPlayerController::StaticClass();
    HUDClass = AWarQuestHud::StaticClass();
}

bool AWarGameMode::IsDevelopmentSession() const
{
    return WarValidation::AllowsDevelopmentNetwork(UE_BUILD_SHIPPING != 0,
        GetNetMode() == NM_Standalone || FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking")));
}

bool AWarGameMode::IsLoopbackProofAddress(const FString& Address)
{
    // PreLogin receives the connection's numeric address, never a client option.
    return Address == TEXT("127.0.0.1") || Address == TEXT("::1") || Address == TEXT("::ffff:127.0.0.1");
}

void AWarGameMode::PreLogin(const FString& Options, const FString& Address,
    const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
    Super::PreLogin(Options, Address, UniqueId, ErrorMessage);
    if (!ErrorMessage.IsEmpty()) return;
    // An online subsystem ID alone is not proof of Steam ownership or backend session authorization.
    if (!IsDevelopmentSession())
        ErrorMessage = TEXT("Production admission is unavailable. Development servers require -WarDevelopmentNetworking in a non-Shipping build.");
    else if (!IsLoopbackProofAddress(Address))
        ErrorMessage = TEXT("Remote admission is closed. Development proof flags authorize loopback tests only.");
}

void AWarGameMode::RejectEntry(APlayerController* Controller, const FString& Error) const
{
    UE_LOG(LogAegisWar, Error, TEXT("Player entry refused: %s"), *Error);
    if (AWarPlayerController* Player = Cast<AWarPlayerController>(Controller))
        Player->RecordEntryFailure(FText::FromString(Error));
}

UWarCharacterVisualDefinition* AWarGameMode::ResolveVisual(AController* Controller, FString& OutError) const
{
    const UWarContentSubsystem* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    if (!Content || !Content->IsContentReady())
    {
        OutError = Content ? Content->GetValidationError() : TEXT("Content subsystem is unavailable.");
        return nullptr;
    }
    for (TActorIterator<AWarQuestNpc> It(GetWorld()); It; ++It)
    {
        FString Name;
        if (!It->ValidateIdentity(Name, OutError)) return nullptr;
    }
    const AWarPlayerState* State = Controller ? Controller->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!State || State->GetRealm() == EWarRealm::None)
    {
        OutError = TEXT("Player has no server-assigned realm.");
        return nullptr;
    }
    const UWarRuntimeSettings* Settings = GetDefault<UWarRuntimeSettings>();
    const auto* Player = Cast<AWarPlayerController>(Controller);
    UWarCharacterVisualDefinition* Visual = Player ? Player->GetCreatedCharacterVisual() : nullptr;
    if (!Visual) Visual = (State->GetRealm() == EWarRealm::Aegis
        ? Settings->AegisDevelopmentVisual : Settings->RiftboundDevelopmentVisual).LoadSynchronous();
    if (!Visual)
    {
        OutError = TEXT("Import and configure an authored skeletal character visual before entering the map.");
        return nullptr;
    }
    if (!Visual->ValidateForSpawn(State->GetRealm(), OutError) || !Content->ValidatePlayableVisual(Visual, OutError)) return nullptr;
    return Visual;
}

void AWarGameMode::HandleStartingNewPlayer_Implementation(APlayerController* NewPlayer)
{
    // Automated acceptance fixtures opt into direct entry; ordinary launches start at login.
    const bool bProofEntry = !UE_BUILD_SHIPPING && (
        FParse::Param(FCommandLine::Get(), TEXT("WarNetworkProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarAnimationNetworkProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarWorkshopCombatProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarWorkshopDeploymentProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarZoneNetworkProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarPortalProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarEnemyProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarTrainingDummyProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarAbilityProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarCapitalProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarInterfaceProof"))
        || FParse::Param(FCommandLine::Get(), TEXT("WarCityPopulationProof")));
    if (!bProofEntry)
    {
        if (auto* Player = Cast<AWarPlayerController>(NewPlayer)) Player->ClientOpenFrontend();
        return;
    }
    if (!IsDevelopmentSession())
    {
        RejectEntry(NewPlayer, TEXT("This foundation has no production session authenticator."));
        return;
    }
    if (AWarPlayerState* State = NewPlayer->GetPlayerState<AWarPlayerState>())
    {
        // Alternating realms are only a local development fixture; no client option grants identity.
        if (State->GetRealm() == EWarRealm::None)
            State->SetDevelopmentRealm(DevelopmentJoins++ % 2 == 0 ? EWarRealm::Aegis : EWarRealm::Riftbound);
    }
    FString Error;
    if (!ResolveVisual(NewPlayer, Error)) { RejectEntry(NewPlayer, Error); return; }
    Super::HandleStartingNewPlayer_Implementation(NewPlayer);
}

APawn* AWarGameMode::SpawnDefaultPawnAtTransform_Implementation(AController* NewPlayer, const FTransform& SpawnTransform)
{
    FString Error;
    UWarCharacterVisualDefinition* Visual = ResolveVisual(NewPlayer, Error);
    if (!IsDevelopmentSession() || !Visual)
    {
        RejectEntry(Cast<APlayerController>(NewPlayer), Error.IsEmpty() ? TEXT("Development admission is closed.") : Error);
        return nullptr;
    }
    AWarCharacter* Character = GetWorld()->SpawnActorDeferred<AWarCharacter>(AWarCharacter::StaticClass(),
        SpawnTransform, NewPlayer, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
    if (!Character)
    {
        RejectEntry(Cast<APlayerController>(NewPlayer), TEXT("Character creation failed. Check the selected PlayerStart, collision clearance and server log."));
        return nullptr;
    }
    if (!Character->SetVisualDefinition(Visual, Error))
    {
        Character->Destroy();
        RejectEntry(Cast<APlayerController>(NewPlayer), Error);
        return nullptr;
    }
    Character->FinishSpawning(SpawnTransform);
    if (!IsValid(Character))
    {
        RejectEntry(Cast<APlayerController>(NewPlayer), TEXT("Character could not finish spawning. Move the PlayerStart clear of blocking geometry and retry."));
        return nullptr;
    }
    return Character;
}

void AWarGameMode::RestartPlayerAtPlayerStart(AController* NewPlayer, AActor* StartSpot)
{
    if (!IsValid(NewPlayer)) return;
    if (!IsValid(StartSpot))
    {
        PendingStartDeadlines.Remove(NewPlayer);
        RejectEntry(Cast<APlayerController>(NewPlayer), TEXT("This map has no valid PlayerStart. Add a safe start to the authored map before entry."));
        FailedToRestartPlayer(NewPlayer);
        return;
    }
    if (const auto* Anchor = Cast<AWarZoneAnchor>(StartSpot))
    {
        auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
        auto* PC = Cast<APlayerController>(NewPlayer);
        if (Streaming && !Streaming->IsZoneReady(Anchor->ZoneId, PC))
        {
            FString Error;
            const double Now = GetWorld()->GetTimeSeconds();
            const double Deadline = PendingStartDeadlines.FindOrAdd(NewPlayer, Now + 30.0);
            if (!Streaming->EnsureZone(Anchor->ZoneId, Error) || Now >= Deadline)
            {
                PendingStartDeadlines.Remove(NewPlayer);
                if (Error.IsEmpty())
                {
                    FString Reason;
                    Streaming->IsZoneReady(Anchor->ZoneId, PC, &Reason);
                    UE_LOG(LogAegisWar, Warning, TEXT("Arrival readiness timeout: %s"), *Reason);
                }
                RejectEntry(PC, Error.IsEmpty() ? TEXT("Arrival content did not load. Please retry character entry.") : Error);
                return;
            }
            const TWeakObjectPtr<AController> WeakPlayer = NewPlayer;
            const TWeakObjectPtr<AActor> WeakStart = StartSpot;
            FTimerHandle Retry;
            GetWorldTimerManager().SetTimer(Retry, FTimerDelegate::CreateWeakLambda(this, [this, WeakPlayer, WeakStart]() {
                if (WeakPlayer.IsValid() && !WeakPlayer->GetPawn())
                    RestartPlayerAtPlayerStart(WeakPlayer.Get(), WeakStart.Get());
                else PendingStartDeadlines.Remove(WeakPlayer);
            }), 0.1f, false);
            return;
        }
    }
    PendingStartDeadlines.Remove(NewPlayer);
    Super::RestartPlayerAtPlayerStart(NewPlayer, StartSpot);
}

void AWarGameMode::FailedToRestartPlayer(AController* NewPlayer)
{
    if (!IsValid(NewPlayer)) return;
    PendingStartDeadlines.Remove(NewPlayer);
    const AWarPlayerController* Player = Cast<AWarPlayerController>(NewPlayer);
    if (!Player || Player->GetEntryFailure().IsEmpty())
        RejectEntry(Cast<APlayerController>(NewPlayer), TEXT("Character entry failed. Check imported visuals, player start clearance and the server log."));
    Super::FailedToRestartPlayer(NewPlayer);
}

void AWarGameMode::FinishRestartPlayer(AController* NewPlayer, const FRotator& StartRotation)
{
    Super::FinishRestartPlayer(NewPlayer, StartRotation);
    if (auto* Player = Cast<AWarPlayerController>(NewPlayer)) Player->CompleteCharacterEntry();
}

void AWarGameMode::RespawnAfterDeath(AWarCharacter* Character)
{
    if (!Character || !Character->HasAuthority()) return;
    AController* Controller = Character->GetController();
    if (!Controller) return;
    if (const auto* Zone = AWarZoneAnchor::FindAt(GetWorld(), Character->GetActorLocation()))
        if (auto* State = Controller->GetPlayerState<AWarPlayerState>()) State->SetCurrentZoneTrusted(Zone->ZoneId);
    Controller->UnPossess();
    Character->SetLifeSpan(5.f);
    const TWeakObjectPtr<AController> WeakController = Controller;
    FTimerHandle Timer;
    GetWorldTimerManager().SetTimer(Timer, FTimerDelegate::CreateWeakLambda(this, [this, WeakController]() {
        if (WeakController.IsValid() && !WeakController->GetPawn()) RestartPlayer(WeakController.Get());
    }), 5.f, false);
}

bool AWarGameMode::ShouldSpawnAtStartSpot(AController* Player)
{
    // Unreal caches the original start across deaths; campaign travel must select the current zone instead.
    const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    if (State && AWarZoneAnchor::FindById(GetWorld(), State->GetCurrentZone())) return false;
    return Super::ShouldSpawnAtStartSpot(Player);
}

AActor* AWarGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
    if (auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr; State && State->GetRealm() != EWarRealm::None)
    {
        const FName Zone = State->GetCurrentZone().IsNone()
            ? FName(State->GetRealm() == EWarRealm::Riftbound ? TEXT("riftspire_capital") : TEXT("aegis_capital")) : State->GetCurrentZone();
        if (auto* Anchor = AWarZoneAnchor::FindById(GetWorld(), Zone))
        { State->SetCurrentZoneTrusted(Zone); return Anchor; }
    }
    return Super::ChoosePlayerStart_Implementation(Player);
}
