#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarScenarioInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacterVisualDefinition.h"
#include "WarAbilityRuntime.h"
#include "WarCombatStatus.h"
#include "WarWrathRelic.h"
#include "WarWarpIdol.h"
#include "AbilitySystemComponent.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

bool AWarSiegeGameMode::IsDevelopmentPlaytest() const
{
    return !UE_BUILD_SHIPPING && HasAuthority() && GetNetMode() == NM_DedicatedServer
        && FParse::Param(FCommandLine::Get(), TEXT("WarSiegePlaytest"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking"))
        && UWorld::RemovePIEPrefix(GetWorld()->GetOutermost()->GetName()) == TEXT("/Game/Capitals/Siege/AegisCapital_Siege");
}

bool AWarSiegeGameMode::IsMenuScenario() const
{ return IsDevelopmentPlaytest() && FParse::Param(FCommandLine::Get(),TEXT("WarScenarioMenu")); }

void AWarSiegeGameMode::BeginPlay()
{
    Super::BeginPlay();
    Encounter = GetWorld()->SpawnActor<AWarSiegeEncounter>();
    if (auto* GS = SiegeState(); GS && IsDevelopmentPlaytest())
    {
        GS->bDevelopmentLobby = true;
        GS->bQueuedScenario=GetGameInstance() && GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->IsEnabled();
        GS->Siege.Scenario = GS->bQueuedScenario ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Scenario() : EWarSiegeScenario::LowerCity;
        UpdateLobby();
    }
}

void AWarSiegeGameMode::PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
    Super::PreLogin(Options, Address, UniqueId, ErrorMessage);
    if (ErrorMessage.IsEmpty() && IsMenuScenario() && GetNumPlayers() >= 1)
        ErrorMessage = TEXT("This menu scenario already has its player.");
    if (ErrorMessage.IsEmpty() && IsDevelopmentPlaytest() && GetNumPlayers() >= (GetGameInstance() && GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->IsEnabled() ? 36 : 12))
        ErrorMessage = TEXT("This lower-city playtest already has twelve human participants.");
}

UWarCharacterVisualDefinition* AWarSiegeGameMode::SelectedVisual(AController* Player) const
{
    const auto* Selected = Selections.Find(Player);
    if (Selected) return Selected->Get();
    const auto* PC=Cast<AWarPlayerController>(Player);
    return PC && GetGameInstance() && GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->IsEnabled() ? PC->GetCreatedCharacterVisual() : nullptr;
}

bool AWarSiegeGameMode::SelectRole(AWarPlayerController* Player, int32 ExpectedRound, EWarSiegeRole CombatRole, FString& Error)
{
    auto* GS = SiegeState();
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!IsDevelopmentPlaytest() || !GS || GS->bQueuedScenario || !PS || Player->GetWorld() != GetWorld() || ExpectedRound != GS->RoundId
        || (GS->Siege.Phase != EWarSiegePhase::Waiting && GS->Siege.Phase != EWarSiegePhase::Finished) || uint8(CombatRole) > 2)
    { Error = TEXT("Class selection is available only in the current siege preparation screen."); return false; }
    if (!Battlefield) { Error = TEXT("The siege battlefield is unavailable."); return false; }
    const auto* Entry = Battlefield->Roster.FindByPredicate([&](const auto& E) { return E.Realm == PS->GetRealm() && E.CombatRole == CombatRole; });
    auto* Visual = Entry ? Entry->Visual.LoadSynchronous() : nullptr;
    if (!Visual || !Visual->ValidateForSpawn(PS->GetRealm(), Error))
    { Error = TEXT("This realm's equipped class is not ready: ") + Error; return false; }
    Selections.Add(Player, Visual);
    GS->ReadyPlayers.Remove(PS->GetPlayerId());
    NextLobbyCheck = 0;
    return true;
}

bool AWarSiegeGameMode::SetReady(AWarPlayerController* Player, int32 ExpectedRound, bool Ready, FString& Error)
{
    auto* GS = SiegeState();
    auto* PS = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!IsDevelopmentPlaytest() || !GS || GS->bQueuedScenario || !PS || Player->GetWorld() != GetWorld() || ExpectedRound != GS->RoundId
        || (GS->Siege.Phase != EWarSiegePhase::Waiting && GS->Siege.Phase != EWarSiegePhase::Finished))
    { Error = TEXT("Readiness does not match the current siege round."); return false; }
    if (Ready && (!GS->bContentReady || !SelectedVisual(Player)))
    { Error = TEXT("Choose a reviewed class after all siege content is ready."); return false; }
    if (Ready) GS->ReadyPlayers.AddUnique(PS->GetPlayerId());
    else GS->ReadyPlayers.Remove(PS->GetPlayerId());
    NextLobbyCheck = 0;
    return true;
}

void AWarSiegeGameMode::UpdateLobby()
{
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextLobbyCheck) return;
    NextLobbyCheck = Now + 1;
    auto* GS = SiegeState(); FString Error;
    const bool WasReady = GS->bContentReady;
    const bool Queued = GetGameInstance() && GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->IsEnabled();
    const auto Scenario = Queued ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Scenario() : EWarSiegeScenario::LowerCity;
    const int32 Capacity = Queued ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Capacity() : 6;
    GS->bContentReady = FindBattlefield(Error) && Battlefield->Validate(Error, Scenario);
    if (GS->bContentReady && !WasReady) GS->bContentReady=ValidateEquipmentStaging(Error);
    if (GS->bContentReady && !WasReady) UE_LOG(LogTemp, Display, TEXT("WAR_SIEGE_CONTENT_READY"));
    if (!GS->bContentReady && GS->Status != Error) UE_LOG(LogTemp, Warning, TEXT("WAR_SIEGE_CONTENT_BLOCKED %s"), *Error);
    GS->Status = GS->bContentReady ? (IsMenuScenario()
        ? TEXT("Choose your class and ready up. Bots fill both teams.")
        : TEXT("Choose your class and ready up. Two testers are required; bots fill both teams.")) : Error;
    if (!GS->bContentReady) GS->ReadyPlayers.Reset();
    GS->RosterLabels.Reset();
    int32 Humans = 0, Counts[2] = {};
    bool AllReady = true;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = Cast<AWarPlayerController>(It->Get());
        const auto* PS = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
        if (!PS || PS->GetRealm() == EWarRealm::None) continue;
        ++Humans; ++Counts[PS->GetRealm() == EWarRealm::Aegis ? 0 : 1];
        const bool Ready = GS->ReadyPlayers.Contains(PS->GetPlayerId()) && SelectedVisual(PC);
        AllReady &= Ready;
        const auto* Visual = SelectedVisual(PC);
        FString Class = Visual ? Visual->ClassId.ToString().Replace(TEXT("_"), TEXT(" ")) : TEXT("Choose a class");
        if (Visual)
        {
            TArray<FString> Words; Class.ParseIntoArray(Words, TEXT(" "));
            for (auto& Word : Words) if (!Word.IsEmpty()) Word[0] = FChar::ToUpper(Word[0]);
            Class = FString::Join(Words, TEXT(" "));
        }
        FString RoleLabel = TEXT("Unselected");
        if (Visual && Battlefield) for (const auto& Entry : Battlefield->Roster)
            if (Entry.Realm == PS->GetRealm() && Entry.Visual.Get() == Visual)
            { RoleLabel = Entry.CombatRole == EWarSiegeRole::Tank ? TEXT("Tank") : Entry.CombatRole == EWarSiegeRole::Healer ? TEXT("Healer") : TEXT("Damage"); break; }
        GS->RosterLabels.Add(FString::Printf(TEXT("%s | %s | %s / %s | %s"), *PS->GetPlayerName(),
            PS->GetRealm() == EWarRealm::Aegis ? TEXT("Aegis") : TEXT("Riftbound"), *Class, *RoleLabel, Ready ? TEXT("Ready") : TEXT("Preparing")));
    }
    const auto* Instance=GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>() : nullptr;
    const bool Enough=Instance && Instance->IsEnabled() ? Instance->CanStart(Humans) : Humans >= (IsMenuScenario() ? 1 : 2);
    if (GS->bContentReady && Enough && AllReady && Counts[0] <= Capacity && Counts[1] <= Capacity)
        if (!StartRound(Capacity, GS->RoundId + 1, Scenario, Error))
        { GS->Status = Error; GS->ReadyPlayers.Reset(); }
    GS->ForceNetUpdate();
}

void AWarSiegeGameMode::Logout(AController* Exiting)
{
    if (GetGameInstance()) GetGameInstance()->GetSubsystem<UWarScenarioInstance>()->Disconnect(Cast<AWarPlayerController>(Exiting));
    if (auto* PS = Exiting ? Exiting->GetPlayerState<AWarPlayerState>() : nullptr)
    {
        PS->GetClassAbilities()->Interrupt(); PS->SetSiegeNormalized(false);
        if (auto* GS = SiegeState()) GS->ReadyPlayers.Remove(PS->GetPlayerId());
    }
    if (Encounter) Encounter->Leave(Exiting);
    Selections.Remove(Exiting);
    Super::Logout(Exiting);
    NextLobbyCheck = 0;
}

void AWarSiegeGameMode::PreLoginAsync(const FString& Options,const FString& Address,const FUniqueNetIdRepl& UniqueId,const FOnPreLoginCompleteDelegate& OnComplete)
{
    auto* Instance=GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>() : nullptr;
    if (!Instance || !Instance->IsEnabled()) { Super::PreLoginAsync(Options,Address,UniqueId,OnComplete);return; }
    FString Error;PreLogin(Options,Address,UniqueId,Error);
    if (!Error.IsEmpty()) { OnComplete.ExecuteIfBound(Error);return; }
    Instance->Admit(UGameplayStatics::ParseOption(Options,TEXT("ScenarioTicket")),[OnComplete](FString Result) { OnComplete.ExecuteIfBound(Result); });
}
APlayerController* AWarSiegeGameMode::Login(UPlayer* NewPlayer,ENetRole InRemoteRole,const FString& Portal,const FString& Options,const FUniqueNetIdRepl& UniqueId,FString& ErrorMessage)
{
    auto* PC=Super::Login(NewPlayer,InRemoteRole,Portal,Options,UniqueId,ErrorMessage);
    auto* Instance=GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarScenarioInstance>() : nullptr;
    if (PC && ErrorMessage.IsEmpty() && Instance && Instance->IsEnabled()
        && !Instance->Attach(Cast<AWarPlayerController>(PC),UGameplayStatics::ParseOption(Options,TEXT("ScenarioTicket")),ErrorMessage)) return nullptr;
    return PC;
}
