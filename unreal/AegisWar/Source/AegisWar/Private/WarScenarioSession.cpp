#include "WarScenarioSession.h"
#include "WarScenarioTransport.h"
#include "WarSiegeGameMode.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarSiegeNavigation.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Misc/CommandLine.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"

namespace
{
    FString HostConfigFile() { FString File;return FParse::Value(FCommandLine::Get(),TEXT("WarScenarioHostConfig="),File) ? File : FPaths::ProjectSavedDir()/TEXT("ScenarioHost/host.json"); }
    void ReleaseCampaign(AWarPlayerController* PC,const FString& Host,const FString& Key,const FString& Ticket)
    {
        auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),PC->ScenarioCharacterId);Body->SetStringField(TEXT("ticket"),Ticket);
        const TWeakObjectPtr<AWarPlayerController> Weak=PC;
        WarScenarioTransport::Request(Host,Key,TEXT("POST"),TEXT("/host/released"),Body,
            [Weak](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) {
            if (auto* Player=Weak.Get()) Player->ClientScenarioTravel(Ok ? Data->GetStringField(TEXT("endpoint")) : FString(),
                Ok ? Data->GetStringField(TEXT("ticket")) : Error);
        });
    }
}
bool UWarScenarioSession::CanStart(bool Shipping,ENetMode Mode,EWarRealm Realm) { return false; }
bool UWarScenarioSession::Start(EWarRealm Realm) { Status=TEXT("Enter your character, then queue from the in-game Scenario menu.");return false; }
void UWarScenarioSession::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    NetworkFailure=GEngine->OnNetworkFailure().AddWeakLambda(this,[this](UWorld*,UNetDriver*,ENetworkFailure::Type,const FString& Error) {
        if (!Token.IsEmpty()) { bTravelPending=false;Status=Error; }
    });
    TravelFailure=GEngine->OnTravelFailure().AddWeakLambda(this,[this](UWorld*,ETravelFailure::Type,const FString& Error) {
        if (!Token.IsEmpty()) { bTravelPending=false;Status=Error;Command(TEXT("leaveMatch")); }
    });
}
void UWarScenarioSession::Deinitialize()
{
    if (GEngine) { GEngine->OnNetworkFailure().Remove(NetworkFailure);GEngine->OnTravelFailure().Remove(TravelFailure); }
    Token.Reset();Super::Deinitialize();
}
TStatId UWarScenarioSession::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarScenarioSession,STATGROUP_Tickables); }
void UWarScenarioSession::Connect(AWarPlayerController* PC)
{
    if (!PC || bConnecting || !Token.IsEmpty() || IsRunning()) return;
    SetConnectionStatus(true,TEXT("Connecting to scenario host..."));
    PC->ServerPrepareScenario();
}
void UWarScenarioSession::SetConnectionStatus(bool Pending,const FString& Message)
{ bConnecting=Pending;Status=Message; }
void UWarScenarioSession::RegisterAuthority(AWarPlayerController* PC,const FString& DepartureTicket)
{
    if (!PC || !PC->HasAuthority()) return;
    const auto Fail=[PC,&DepartureTicket](const FString& Error) {
        if (!DepartureTicket.IsEmpty()) PC->ClientScenarioTravel(FString(),Error);
        else PC->ClientScenarioConnectionStatus(false,Error);
    };
    if (UE_BUILD_SHIPPING || Cast<AWarSiegeGameMode>(PC->GetWorld()->GetAuthGameMode()))
    { Fail(TEXT("Scenario queue connection is only available from a development campaign character."));return; }
    if (DepartureTicket.IsEmpty() && PendingRegistrations.Contains(PC)) return;
    auto Config=WarScenarioTransport::ReadConfig(HostConfigFile());
    if (!Config) {
        Fail(TEXT("Scenario host is not configured. Start npm run scenario:host in the project folder, then select Connect / retry."));return;
    }
    FString ProvisionedId;
    if (Config->TryGetStringField(TEXT("characterId"),ProvisionedId))
    {
        if (!PC->ScenarioCharacterId.IsEmpty() && PC->ScenarioCharacterId!=ProvisionedId)
        { Fail(TEXT("This development host config belongs to another character."));return; }
        PC->ScenarioCharacterId=ProvisionedId;
    }
    if (PC->ScenarioCharacterId.IsEmpty()) PC->ScenarioCharacterId=FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Host=Config->GetStringField(TEXT("url")),Key=Config->GetStringField(TEXT("key"));
    if (!DepartureTicket.IsEmpty() && !PC->GetPawn())
    { ReleaseCampaign(PC,Host,Key,DepartureTicket);return; }
    if (const auto* State=PC->GetPlayerState<AWarPlayerState>();State && State->IsScenarioTransferPending())
    { if (DepartureTicket.IsEmpty()) Fail(TEXT("Your character is transferring. Wait for departure to finish."));return; }
    auto Snapshot=WarScenarioTransport::Capture(PC,PC->ScenarioCharacterId);
    if (!Snapshot) {
        Fail(TEXT("Enter a living character before queuing or departing."));return;
    }
    const bool Depart=!DepartureTicket.IsEmpty();
    auto Body=Snapshot;
    if (Depart) { Body=MakeShared<FJsonObject>();Body->SetObjectField(TEXT("character"),Snapshot);Body->SetStringField(TEXT("ticket"),DepartureTicket); }
    const TWeakObjectPtr<AWarPlayerController> Weak=PC;
    const TWeakObjectPtr<APawn> Pawn=PC->GetPawn();
    const TWeakObjectPtr<AWarPlayerState> State=PC->GetPlayerState<AWarPlayerState>();
    const auto* Character=Cast<AWarCharacter>(Pawn.Get());
    const EMovementMode PreviousMode=Character->GetCharacterMovement()->MovementMode;
    const uint8 PreviousCustomMode=Character->GetCharacterMovement()->CustomMovementMode;
    if (Depart)
    {
        State->SetScenarioTransferPending(true);
        Character->GetCharacterMovement()->StopMovementImmediately();Character->GetCharacterMovement()->DisableMovement();
    }
    else
    {
        PendingRegistrations.Add(PC);
        PC->ClientScenarioConnectionStatus(true,TEXT("Connecting to scenario host..."));
    }
    const TWeakObjectPtr<UWarScenarioSession> Session=this;
    WarScenarioTransport::Request(Host,Key,TEXT("POST"),Depart ? TEXT("/host/depart") : TEXT("/host/register"),Body,
        [Session,Weak,Pawn,State,PreviousMode,PreviousCustomMode,Host,Key,Depart,DepartureTicket](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) {
        if (!Depart && Session.IsValid()) Session->PendingRegistrations.Remove(Weak);
        if (Depart && State.IsValid()) State->SetScenarioTransferPending(false);
        if (Depart) if (auto* Avatar=Cast<AWarCharacter>(Pawn.Get())) Avatar->GetCharacterMovement()->SetMovementMode(PreviousMode,PreviousCustomMode);
        auto* Player=Weak.Get();if (!Player) return;
        if (!Ok) { if (Depart) Player->ClientScenarioTravel(FString(),Error);else Player->ClientScenarioConnectionStatus(false,Error);return; }
        if (Depart)
        {
            if (Player->GetPawn()!=Pawn.Get() || !Pawn.IsValid()) { Player->ClientScenarioTravel(FString(),TEXT("Your character changed before departure. Retry the queue."));return; }
            // The authoritative campaign pawn is removed before a match can possess its snapshot.
            Player->UnPossess();Pawn->Destroy();
            ReleaseCampaign(Player,Host,Key,DepartureTicket);
        }
        else Player->ClientScenarioRegistered(Host,Data->GetStringField(TEXT("token")),Player->ScenarioCharacterId);
    });
}
void UWarScenarioSession::SetCredentials(const FString& Host,const FString& Credential,const FString& Id)
{ Url=Host;Token=Credential;CharacterId=Id;NextPoll=0;SetConnectionStatus(false,TEXT("Connected to scenario queue.")); }
void UWarScenarioSession::Command(const FString& Action,const FString& Target)
{
    if (Token.IsEmpty()) { Status=TEXT("Start the scenario host, then reopen this panel from a living character.");return; }
    auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("action"),Action);Body->SetStringField(TEXT("target"),Target);
    Body->SetStringField(TEXT("requestId"),FGuid::NewGuid().ToString(EGuidFormats::Digits));
    const TWeakObjectPtr<UWarScenarioSession> Weak=this;
    WarScenarioTransport::Request(Url,Token,TEXT("POST"),TEXT("/command"),Body,[Weak](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) {
        if (auto* Self=Weak.Get()) { if (Ok) Self->ApplyView(Data);else Self->Status=Error; }
    });
}
void UWarScenarioSession::Cancel() { Command(TEXT("cancel")); }
void UWarScenarioSession::Leave() { Command(TEXT("leaveMatch")); }
void UWarScenarioSession::Travel(const FString& Endpoint,const FString& Ticket)
{
    if (Endpoint.IsEmpty()) { bTravelPending=false;Status=Ticket;NextPoll=FPlatformTime::Seconds()+2;return; }
    auto* PC=GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;if (!PC) return;
    bInScenario=true;bTravelPending=true;
    UWidgetLayoutLibrary::RemoveAllWidgets(this);
    PC->ClientTravel(Endpoint+TEXT("?ScenarioTicket=")+Ticket,TRAVEL_Absolute);
}
void UWarScenarioSession::ApplyView(TSharedPtr<FJsonObject> Data)
{
    if (!Data) return;
    View=Data;const FString Previous=Phase;Phase=Data->GetStringField(TEXT("phase"));Data->TryGetStringField(TEXT("message"),Status);
    if (Phase==TEXT("idle")) bTravelPending=false;
    auto* PC=GetWorld() ? Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()) : nullptr;
    if (!PC) return;
    if (bInScenario && !PC->GetPawn() && !PC->IsInterfaceOpen()) PC->ShowInterface(TEXT("Scenario"));
    if (Phase==TEXT("playing") && PC->GetPawn() && bTravelPending)
    { bTravelPending=false;PC->CloseInterface(); }
    if (Phase==TEXT("idle") && bReturnPawnReady)
    {
        ReturnTicket.Reset();bInScenario=false;bReturnPending=false;bReturnPawnReady=false;
        PC->CloseInterface();
        Status=TEXT("Returned to your campaign character.");
    }
    if (Phase==TEXT("offered") && Previous!=Phase) PC->ShowInterface(TEXT("Scenario"));
    if (Phase==TEXT("travel") && !bTravelPending)
    {
        FString Ticket;if (!Data->TryGetStringField(TEXT("ticket"),Ticket)) return;
        bTravelPending=true;
        if (bInScenario) Travel(Data->GetObjectField(TEXT("match"))->GetStringField(TEXT("endpoint")),Ticket);
        else PC->ServerScenarioDepart(Ticket);
    }
    if (Phase==TEXT("return"))
    {
        if (!Data->TryGetStringField(TEXT("ticket"),ReturnTicket) || !Data->TryGetStringField(TEXT("returnMap"),ReturnMap)) return;
        if (bReturnPending) return;
        bReturnPending=true;bTravelPending=false;UWidgetLayoutLibrary::RemoveAllWidgets(this);
        UGameplayStatics::OpenLevel(this,FName(*ReturnMap));
    }
}
void UWarScenarioSession::Tick(float Delta)
{
    if (bPolling || FPlatformTime::Seconds()<NextPoll) return;
    if (bReturnPending)
    {
        auto* PC=GetWorld() ? Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()) : nullptr;
        if (PC && PC->HasAuthority())
        {
            if (bReturnPawnReady) CompleteReturn(PC);
            else if (!PC->GetPawn()) RestorePending(PC);
        }
    }
    NextPoll=FPlatformTime::Seconds()+1;bPolling=true;
    const TWeakObjectPtr<UWarScenarioSession> Weak=this;
    WarScenarioTransport::Request(Url,Token,TEXT("GET"),TEXT("/status"),nullptr,[Weak](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) {
        if (auto* Self=Weak.Get()) { Self->bPolling=false;if (Ok) Self->ApplyView(Data);else Self->Status=Error; }
    });
}
bool UWarScenarioSession::RestorePending(AWarPlayerController* PC)
{
    if (ReturnTicket.IsEmpty() || !PC || !PC->HasAuthority()) return false;
    if (bRestoreInFlight) return true;
    auto Config=WarScenarioTransport::ReadConfig(HostConfigFile());
    if (!Config) return false;
    bRestoreInFlight=true;
    auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("ticket"),ReturnTicket);Body->SetStringField(TEXT("id"),CharacterId);
    const TWeakObjectPtr<UWarScenarioSession> Weak=this;const TWeakObjectPtr<AWarPlayerController> Player=PC;
    WarScenarioTransport::Request(Config->GetStringField(TEXT("url")),Config->GetStringField(TEXT("key")),TEXT("POST"),TEXT("/host/restore"),Body,
        [Weak,Player](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) {
        auto* Self=Weak.Get();auto* Controller=Player.Get();if (!Self || !Controller) return;
        Self->bRestoreInFlight=false;
        if (!Ok || !WarScenarioTransport::Restore(Controller,Data,false,Error)) { Self->Status=Error;Controller->ClientWorldEditResult(Error);return; }
        const auto& P=Data->GetArrayField(TEXT("returnPosition"));Self->ReturnPosition=FVector(P[0]->AsNumber(),P[1]->AsNumber(),P[2]->AsNumber());
        const TSharedPtr<FJsonObject>* Runtime=nullptr;
        if (Data->GetObjectField(TEXT("document"))->TryGetObjectField(TEXT("runtime"),Runtime)) Self->ReturnRuntime=*Runtime;
        if (auto* Mode=Controller->GetWorld()->GetAuthGameMode<AWarGameMode>()) Mode->RestartPlayer(Controller);
    });
    return true;
}
void UWarScenarioSession::CompleteReturn(AWarPlayerController* PC)
{
    if (ReturnTicket.IsEmpty() || !PC || !PC->GetPawn()) return;
    auto* Pawn=Cast<AWarCharacter>(PC->GetPawn());FVector Center;
    if (!bReturnPawnReady && Pawn && WarSiegeNavigation::SpawnCandidate(GetWorld(),ReturnPosition-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3),
        Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius(),Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),Center))
        Pawn->TeleportTo(Center,Pawn->GetActorRotation(),false,true);
    bReturnPawnReady=true;
    if (ReturnRuntime) { if (auto* PS=PC->GetPlayerState<AWarPlayerState>()) PS->RestoreScenarioState(ReturnRuntime);ReturnRuntime.Reset(); }
    if (bReturnAckInFlight) return;
    auto Config=WarScenarioTransport::ReadConfig(HostConfigFile());if (!Config) return;
    auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("ticket"),ReturnTicket);Body->SetStringField(TEXT("id"),CharacterId);
    bReturnAckInFlight=true;
    const TWeakObjectPtr<UWarScenarioSession> Weak=this;
    WarScenarioTransport::Request(Config->GetStringField(TEXT("url")),Config->GetStringField(TEXT("key")),TEXT("POST"),TEXT("/host/restored"),Body,
        [Weak](bool Ok,TSharedPtr<FJsonObject>,FString Error) {
        if (auto* Self=Weak.Get()) { Self->bReturnAckInFlight=false;if (!Ok) Self->Status=Error;Self->NextPoll=0; }
    });
}
